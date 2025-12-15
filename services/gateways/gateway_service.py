"""
gateway_service.py
Gateway creation, deletion, and management.
"""
import os
import json
import boto3
from botocore.exceptions import ClientError

AWS_REGION = os.environ.get("AWS_DEFAULT_REGION", "us-east-1")
ROLE_NAME = "sample-lambdagateway-role-demo"


def create_agentcore_gateway_role(role_name: str, region: str = None) -> str:
    """
    Create an IAM role for the AgentCore Gateway.

    Creates a role that allows the bedrock-agentcore service to assume it with a broad policy
    for gateways management. Adjust permissions to least privilege as needed for production.

    Args:
        role_name: Name of the IAM role to create
        region: Optional AWS region

    Returns:
        Role ARN string
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

    # Attach inline policy for gateways management
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
        print("Warning attaching inline policy:", e)

    return role_arn


def _create_gateway_with_auth(gateway_name: str, role_arn: str, auth_config: dict, description: str) -> dict:
    """Create a gateways with JWT authentication."""
    session = boto3.Session(region_name=AWS_REGION)
    gateway_client = session.client("bedrock-agentcore-control")

    jwt_auth_config = {
        "customJWTAuthorizer": {
            "allowedClients": [auth_config["client_id"]],
            "discoveryUrl": auth_config["discovery_url"]
        }
    }

    return gateway_client.create_gateway(
        name=gateway_name,
        roleArn=role_arn,
        protocolType="MCP",
        authorizerType="CUSTOM_JWT",
        authorizerConfiguration=jwt_auth_config,
        description=description or "AgentCore Gateway with OpenAPI targets"
    )


def _create_gateway_without_auth(gateway_name: str, role_arn: str, description: str) -> dict:
    """Create a gateways without authentication."""
    session = boto3.Session(region_name=AWS_REGION)
    gateway_client = session.client("bedrock-agentcore-control")

    return gateway_client.create_gateway(
        name=gateway_name,
        roleArn=role_arn,
        protocolType="MCP",
        authorizerType="NONE",
        description=description or "AgentCore Gateway without authentication"
    )


def create_gateway(gateway_name: str, role_arn: str, is_authenticated: bool, auth_config: dict = None, description: str = None) -> dict:
    """
    Create a gateways.

    Args:
        gateway_name: Name of the gateways
        role_arn: ARN of IAM role for the gateways
        is_authenticated: If True, creates gateways with JWT auth; if False, no auth
        auth_config: Required if is_authenticated=True; dict with client_id and discovery_url
        description: Optional gateways description

    Returns:
        dict with gateway_id, gateway_url, and gateway_name

    Raises:
        ValueError: If validation fails
        ClientError: If AWS API call fails
    """
    print(f"Creating gateways: {gateway_name}...")

    try:
        if is_authenticated:
            create_response = _create_gateway_with_auth(gateway_name, role_arn, auth_config, description)
            print("✓ Gateway created with JWT auth.")
        else:
            create_response = _create_gateway_without_auth(gateway_name, role_arn, description)
            print("✓ Gateway created without auth.")
    except ClientError as e:
        raise


    print("Gateway info:")
    for k, v in create_response.items():
        print(f"  {k}: {v}")

    gateway_id = create_response.get("gatewayId")
    gateway_url = create_response.get("gatewayUrl")
    print(f"Gateway ID: {gateway_id}")
    print(f"Gateway URL: {gateway_url}")

    if not gateway_id or not gateway_url:
        raise ValueError(f"Invalid gateway response: {create_response}")

    return create_response


def update_gateway(
    gateway_id: str,
    name: str,
    protocol_type: str,
    authorizer_type: str,
    role_arn: str,
    description: str = None,
    authorizer_configuration: dict = None
) -> dict:
    """
    Update an existing gateway.

    Docs: https://docs.aws.amazon.com/bedrock-agentcore-control/latest/APIReference/API_UpdateGateway.html

    Args:
        gateway_id: The unique identifier of the gateway to update
        name: The name of the gateway (must match original name)
        protocol_type: The protocol type (MCP)
        authorizer_type: The authorizer type (CUSTOM_JWT, AWS_IAM, NONE)
        role_arn: The IAM role ARN for the gateway
        description: Optional updated description
        authorizer_configuration: Optional updated authorizer configuration

    Returns:
        dict: Update response containing:
            - gatewayId (str): Gateway identifier
            - gatewayUrl (str): Gateway endpoint URL
            - name (str): Gateway name
            - status (str): Current status (UPDATING, READY, etc.)
            - gatewayArn (str): Gateway ARN
            - description (str): Gateway description
            - createdAt (str): Creation timestamp
            - updatedAt (str): Last update timestamp
            - authorizerType (str): Authorizer type
            - protocolType (str): Protocol type
            - roleArn (str): IAM role ARN
            - statusReasons (list): Reasons for current status

    Raises:
        ValueError: If gateway not found
        ClientError: If AWS API call fails
    """
    session = boto3.Session(region_name=AWS_REGION)
    gateway_client = session.client("bedrock-agentcore-control")

    print(f"Updating gateway: {gateway_id}...")

    # Build update parameters
    update_params = {
        "gatewayIdentifier": gateway_id,
        "name": name,
        "protocolType": protocol_type,
        "authorizerType": authorizer_type,
        "roleArn": role_arn
    }

    # Add optional parameters if provided
    if description is not None:
        update_params["description"] = description

    if authorizer_configuration is not None:
        update_params["authorizerConfiguration"] = authorizer_configuration

    try:
        response = gateway_client.update_gateway(**update_params)
        print("✓ Gateway updated.")

        # Log key response details
        print(f"  Gateway ID: {response.get('gatewayId')}")
        print(f"  Gateway URL: {response.get('gatewayUrl')}")
        print(f"  Status: {response.get('status')}")
        print(f"  Name: {response.get('name')}")
        if response.get('updatedAt'):
            print(f"  Updated At: {response.get('updatedAt')}")
        if response.get('statusReasons'):
            print(f"  Status Reasons: {response.get('statusReasons')}")

        return response
    except ClientError as e:
        error_code = e.response["Error"]["Code"]
        if error_code == "ResourceNotFoundException":
            raise ValueError(f"Gateway '{gateway_id}' not found")
        else:
            raise


def delete_gateway(gateway_id: str) -> None:
    """
    Delete a gateways by ID.

    Args:
        gateway_id: The ID of the gateways to delete

    Raises:
        Exception: If AWS API call fails
    """
    session = boto3.Session(region_name=AWS_REGION)
    gateway_client = session.client("bedrock-agentcore-control")

    try:
        print(f"Deleting gateways {gateway_id}...")
        gateway_client.delete_gateway(gatewayId=gateway_id)
        print("✓ Gateway deleted.")
    except Exception as e:
        print(f"delete gateways error: {e}")
        raise

