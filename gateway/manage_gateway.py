"""
manage_gateway.py
Creates, updates, retrieves, or deletes an AgentCore Gateway (MCP server).
Depends on authentication infrastructure already being set up.
"""
import os
import json
import boto3
from botocore.exceptions import ClientError

# CONFIG: change these as needed
AWS_REGION = os.environ.get("AWS_DEFAULT_REGION", "us-east-1")
GATEWAY_NAME = "DemoGWOpenAPIAPIKeyNasaOAI"
ROLE_NAME = "sample-lambdagateway-role-demo"

# Auth config - pass these from auth module
AUTH_CONFIG = {
    "user_pool_id": None,  # Required: from setup_auth
    "client_id": None,  # Required: from setup_auth
    "discovery_url": None,  # Required: from setup_auth
}


def create_agentcore_gateway_role(role_name: str, region: str = None):
    """
    Create an IAM role for the AgentCore Gateway to assume with a minimal policy that allows
    the gateway service to manage itself. Adjust permissions to least privilege as required.
    Returns the create_role response.
    """
    iam = boto3.client("iam", region_name=region)
    assume_role_policy = {
        "Version": "2012-10-17",
        "Statement": [
            {
                "Effect": "Allow",
                "Principal": {"Service": "bedrock-agentcore.amazonaws.com"},
                "Action": "sts:AssumeRole"
            }
        ]
    }

    try:
        resp = iam.create_role(
            RoleName=role_name,
            AssumeRolePolicyDocument=json.dumps(assume_role_policy),
            Description="Role for Bedrock AgentCore Gateway"
        )
        role_arn = resp["Role"]["Arn"]
    except ClientError as e:
        if e.response['Error']['Code'] == 'EntityAlreadyExists':
            resp = iam.get_role(RoleName=role_name)
            role_arn = resp['Role']['Arn']
        else:
            raise

    # Attach a broad but example inline policy for Gateway management.
    # You should narrow this down for production.
    policy_document = {
        "Version": "2012-10-17",
        "Statement": [
            {
                "Effect": "Allow",
                "Action": [
                    "bedrock-agentcore-control:*",
                    "s3:GetObject",
                    "s3:PutObject",
                    "s3:ListBucket",
                    "iam:PassRole",
                    "cognito-idp:*",
                    "sts:GetCallerIdentity"
                ],
                "Resource": "*"
            },
            {
                "Effect": "Allow",
                "Action": [
                    "bedrock-agentcore:GetWorkloadAccessToken",
                    "bedrock-agentcore:InvokeCredentialProvider",
                    "bedrock-agentcore:GetResourceApiKey"
                ],
                "Resource": "*"
            },
            {
                "Effect": "Allow",
                "Action": [
                    "secretsmanager:GetSecretValue"
                ],
                "Resource": "*"
            }
        ]
    }

    try:
        iam.put_role_policy(
            RoleName=role_name,
            PolicyName=f"{role_name}-inline-policy",
            PolicyDocument=json.dumps(policy_document)
        )
    except Exception as e:
        # warn but continue
        print("Warning attaching inline policy:", e)

    return {"Role": {"Arn": role_arn}}


def create_or_get_gateway(gateway_name: str, auth_config: dict, description: str = None):
    """
    Creates a new gateway or retrieves an existing one by name.

    Args:
        gateway_name: Name of the gateway
        auth_config: Dict containing role_arn, client_id, discovery_url
        description: Optional description for the gateway

    Returns:
        dict with gateway_id and gateway_url
    """
    session = boto3.Session(region_name=AWS_REGION)
    gateway_client = session.client("bedrock-agentcore-control")

    # Validate required auth config
    required_keys = ["role_arn", "client_id", "discovery_url"]
    for key in required_keys:
        if key not in auth_config or not auth_config[key]:
            raise ValueError(f"Missing required auth_config key: {key}")

    # Build JWT auth configuration
    jwt_auth_config = {
        "customJWTAuthorizer": {
            "allowedClients": [auth_config["client_id"]],
            "discoveryUrl": auth_config["discovery_url"]
        }
    }

    print(f"Creating/retrieving gateway: {gateway_name}...")
    try:
        create_response = gateway_client.create_gateway(
            name=gateway_name,
            roleArn=auth_config["role_arn"],
            protocolType="MCP",
            authorizerType="CUSTOM_JWT",
            authorizerConfiguration=jwt_auth_config,
            description=description or "AgentCore Gateway with OpenAPI targets"
        )
        print("✓ Gateway created.")
    except ClientError as e:
        if e.response["Error"]["Code"] == "ConflictException":
            # Gateway name exists; find it by listing
            print("Gateway name exists; retrieving existing gateway...")
            gw_list = gateway_client.list_gateways().get("gateways", [])
            create_response = None
            for g in gw_list:
                if g["name"] == gateway_name:
                    create_response = g
                    break
            if create_response is None:
                raise ValueError(f"Gateway '{gateway_name}' conflict but not found in list")
            print("✓ Retrieved existing gateway.")
        else:
            raise

    # Print all gateway info
    print("Gateway info:")
    for k, v in create_response.items():
        print(f"  {k}: {v}")

    # Extract gateway info
    gateway_id = create_response.get("gatewayId")
    gateway_url = create_response.get("gatewayUrl")

    if not gateway_id or not gateway_url:
        raise ValueError(f"Invalid gateway response: {create_response}")

    print(f"Gateway ID: {gateway_id}")
    print(f"Gateway URL: {gateway_url}")

    return {
        "gateway_id": gateway_id,
        "gateway_url": gateway_url,
        "gateway_name": gateway_name
    }



def create_or_get_gateway_no_auth(gateway_name: str, role_arn: str, description: str = None):
    """
    Creates a new gateway without authentication or retrieves an existing one by name.

    Docs: https://docs.aws.amazon.com/bedrock-agentcore-control/latest/APIReference/API_CreateGateway.html

    Args:
        gateway_name: Name of the gateway
        role_arn: ARN of the IAM role for the gateway
        description: Optional description for the gateway

    Returns:
        dict with gateway_id and gateway_url
    """
    session = boto3.Session(region_name=AWS_REGION)
    gateway_client = session.client("bedrock-agentcore-control")

    print(f"Creating/retrieving gateway (no auth): {gateway_name}...")
    try:
        create_response = gateway_client.create_gateway(
            name=gateway_name,
            roleArn=role_arn,
            protocolType="MCP",
            authorizerType="NONE",
            description=description or "AgentCore Gateway without authentication"
        )
        print("✓ Gateway created (no auth).")
    except ClientError as e:
        if e.response["Error"]["Code"] == "ConflictException":
            # Gateway name exists; find it by listing
            print("Gateway name exists; retrieving existing gateway...")
            gw_list = gateway_client.list_gateways().get("gateways", [])
            create_response = None
            for g in gw_list:
                if g["name"] == gateway_name:
                    create_response = g
                    break
            if create_response is None:
                raise ValueError(f"Gateway '{gateway_name}' conflict but not found in list")
            print("✓ Retrieved existing gateway.")
        else:
            raise

    # Print all gateway info
    print("Gateway info:")
    for k, v in create_response.items():
        print(f"  {k}: {v}")

    # Extract gateway info
    gateway_id = create_response.get("gatewayId")
    gateway_url = create_response.get("gatewayUrl")

    if not gateway_id or not gateway_url:
        raise ValueError(f"Invalid gateway response: {create_response}")

    print(f"Gateway ID: {gateway_id}")
    print(f"Gateway URL: {gateway_url}")

    return {
        "gateway_id": gateway_id,
        "gateway_url": gateway_url,
        "gateway_name": gateway_name
    }


def delete_gateway(gateway_id: str):
    """
    Deletes a gateway by ID.

    Args:
        gateway_id: The ID of the gateway to delete
    """
    session = boto3.Session(region_name=AWS_REGION)
    gateway_client = session.client("bedrock-agentcore-control")

    try:
        print(f"Deleting gateway {gateway_id}...")
        gateway_client.delete_gateway(gatewayId=gateway_id)
        print("✓ Gateway deleted.")
    except Exception as e:
        print(f"delete gateway error: {e}")
        raise


def setup_gateway(gateway_name: str, auth_config: dict, description: str = None):
    """
    Main entry point: creates or retrieves a gateway.
    Creates the IAM role and gateway.

    Args:
        gateway_name: Name of the gateway
        auth_config: Authentication config from auth module (user_pool_id, client_id, discovery_url)
        description: Optional gateway description

    Returns:
        dict with gateway_id, gateway_url, and gateway_name
    """
    # Create IAM role for gateway
    print("Creating or reusing IAM role for gateway...")
    gateway_role = create_agentcore_gateway_role(ROLE_NAME, region=AWS_REGION)
    auth_config["role_arn"] = gateway_role["Role"]["Arn"]
    print(f"Role ARN: {auth_config['role_arn']}")

    gateway_info = create_or_get_gateway(gateway_name, auth_config, description)
    return gateway_info


def setup_gateway_no_auth(gateway_name: str, description: str = None):
    """
    Creates or retrieves a gateway without authentication.
    Creates the IAM role and gateway.

    Args:
        gateway_name: Name of the gateway
        description: Optional gateway description

    Returns:
        dict with gateway_id, gateway_url, and gateway_name
    """
    # Create IAM role for gateway
    print("Creating or reusing IAM role for gateway...")
    gateway_role = create_agentcore_gateway_role(ROLE_NAME, region=AWS_REGION)
    role_arn = gateway_role["Role"]["Arn"]
    print(f"Role ARN: {role_arn}")

    gateway_info = create_or_get_gateway_no_auth(gateway_name, role_arn, description)
    return gateway_info


if __name__ == "__main__":
    # Example usage
    print("To use this module, import it and call:")
    print("  from gateway import setup_gateway")
    print("  from auth import setup_auth")
    print("")
    print("  auth_config = setup_auth()")
    print("  gateway_info = setup_gateway('MyGatewayName', auth_config)")
    print("")
    print("Or provide AUTH_CONFIG in this file and run directly.")

