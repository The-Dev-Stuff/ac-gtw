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
    for gateway management. Adjust permissions to least privilege as needed for production.

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

    # Attach inline policy for gateway management
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



def _extract_gateway_info(gateway_response: dict) -> tuple:
    """Extract and print gateway ID and URL from response."""
    print("Gateway info:")
    for k, v in gateway_response.items():
        print(f"  {k}: {v}")

    gateway_id = gateway_response.get("gatewayId")
    gateway_url = gateway_response.get("gatewayUrl")
    print(f"Gateway ID: {gateway_id}")
    print(f"Gateway URL: {gateway_url}")

    return gateway_id, gateway_url


def _create_gateway_with_auth(gateway_name: str, role_arn: str, auth_config: dict, description: str) -> dict:
    """Create a gateway with JWT authentication."""
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
    """Create a gateway without authentication."""
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
    Create a gateway.

    Args:
        gateway_name: Name of the gateway
        role_arn: ARN of IAM role for the gateway
        is_authenticated: If True, creates gateway with JWT auth; if False, no auth
        auth_config: Required if is_authenticated=True; dict with client_id and discovery_url
        description: Optional gateway description

    Returns:
        dict with gateway_id, gateway_url, and gateway_name

    Raises:
        ValueError: If validation fails
        ClientError: If AWS API call fails
    """
    print(f"Creating gateway: {gateway_name}...")

    try:
        if is_authenticated:
            create_response = _create_gateway_with_auth(gateway_name, role_arn, auth_config, description)
            print("✓ Gateway created with JWT auth.")
        else:
            create_response = _create_gateway_without_auth(gateway_name, role_arn, description)
            print("✓ Gateway created without auth.")
    except ClientError as e:
        raise

    gateway_id, gateway_url = _extract_gateway_info(create_response)

    if not gateway_id or not gateway_url:
        raise ValueError(f"Invalid gateway response: {create_response}")

    return {
        "gateway_id": gateway_id,
        "gateway_url": gateway_url,
        "gateway_name": gateway_name
    }


def delete_gateway(gateway_id: str) -> None:
    """
    Delete a gateway by ID.

    Args:
        gateway_id: The ID of the gateway to delete

    Raises:
        Exception: If AWS API call fails
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

