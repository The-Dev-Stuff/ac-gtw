"""
tools_service.py
Gateway target (tool) creation and deletion.
Handles OpenAPI schema registration with credential injection.
"""
import os
import boto3
from botocore.exceptions import ClientError

AWS_REGION = os.environ.get("AWS_DEFAULT_REGION", "us-east-1")


def create_gateway_target(
    gateway_id: str,
    target_name: str,
    openapi_s3_uri: str,
    api_key_credential_provider_arn: str,
    api_key_param_name: str = "api_key",
    api_key_location: str = "QUERY_PARAMETER",
    description: str = None
) -> dict:
    """
    Create a gateway target (tool) with OpenAPI spec and credential injection.

    OpenAPI schema targets require either OAUTH or API_KEY credential provider.

    Docs: https://docs.aws.amazon.com/bedrock-agentcore-control/latest/APIReference/API_CreateGatewayTarget.html

    Args:
        gateway_id: ID of the gateway
        target_name: Name of the target
        openapi_s3_uri: S3 URI of the OpenAPI spec
        api_key_credential_provider_arn: ARN of credential provider for API key injection
        api_key_param_name: Parameter name for the API key (e.g., "api_key", "Authorization")
        api_key_location: Where to inject the key: "QUERY_PARAMETER" or "HEADER"
        description: Optional target description

    Returns:
        dict: Target creation response containing:
            - targetId (str): Unique identifier of the created target
            - name (str): Name of the target
            - status (str): Current status (CREATING, UPDATING, READY, FAILED, etc.)
            - gatewayArn (str): ARN of the gateway
            - description (str): Description of the target
            - createdAt (str): Timestamp when the target was created
            - updatedAt (str): Timestamp when target was last updated
            - lastSynchronizedAt (str): Last synchronization timestamp
            - statusReasons (list): Reasons for current status
            - targetConfiguration (dict): Configuration settings for the target
            - credentialProviderConfigurations (list): Credential provider configurations

    Raises:
        ValueError: If target name already exists on the gateway
        ClientError: If AWS API call fails
    """
    session = boto3.Session(region_name=AWS_REGION)
    gateway_client = session.client("bedrock-agentcore-control")

    print(f"Creating gateway target: {target_name}")

    # Build target configuration with OpenAPI schema
    target_config = {
        "mcp": {
            "openApiSchema": {
                "s3": {
                    "uri": openapi_s3_uri
                }
            }
        }
    }

    # Build credential provider configuration
    # OpenAPI schema targets only support OAUTH and API_KEY types
    credential_configs = [
        {
            "credentialProviderType": "API_KEY",
            "credentialProvider": {
                "apiKeyCredentialProvider": {
                    "credentialParameterName": api_key_param_name,
                    "providerArn": api_key_credential_provider_arn,
                    "credentialLocation": api_key_location
                }
            }
        }
    ]

    # Create the target
    try:
        create_response = gateway_client.create_gateway_target(
            gatewayIdentifier=gateway_id,
            name=target_name,
            description=description or f"OpenAPI target: {target_name}",
            targetConfiguration=target_config,
            credentialProviderConfigurations=credential_configs
        )
        print("✓ Gateway target created.")

        # Log key response details
        print(f"  Target ID: {create_response.get('targetId')}")
        print(f"  Gateway ARN: {create_response.get('gatewayArn')}")
        print(f"  Status: {create_response.get('status')}")
        print(f"  Name: {create_response.get('name')}")
        if create_response.get('createdAt'):
            print(f"  Created At: {create_response.get('createdAt')}")
        if create_response.get('statusReasons'):
            print(f"  Status Reasons: {create_response.get('statusReasons')}")

        return create_response
    except ClientError as e:
        if e.response["Error"]["Code"] == "ConflictException":
            print("✗ Target name already exists for this gateway.")
            raise ValueError(f"Target '{target_name}' already exists on gateway {gateway_id}")
        else:
            raise


def delete_gateway_target(gateway_id: str, target_id: str) -> dict:
    """
    Delete a gateway target (tool) from a gateway.

    Docs: https://docs.aws.amazon.com/bedrock-agentcore-control/latest/APIReference/API_DeleteGatewayTarget.html

    Args:
        gateway_id: The unique identifier of the gateway
        target_id: The unique identifier of the target to delete

    Returns:
        dict: Deletion response containing:
            - targetId (str): ID of the deleted target
            - gatewayArn (str): ARN of the gateway
            - status (str): Current status (DELETING, etc.)
            - statusReasons (list): Reasons for current status

    Raises:
        ValueError: If target not found on gateway
        ClientError: If AWS API call fails
    """
    session = boto3.Session(region_name=AWS_REGION)
    gateway_client = session.client("bedrock-agentcore-control")

    print(f"Deleting gateway target: {target_id} from gateway: {gateway_id}")

    try:
        response = gateway_client.delete_gateway_target(
            gatewayIdentifier=gateway_id,
            targetId=target_id
        )
        print(f"✓ Gateway target deletion initiated. Status: {response.get('status')}")
        return response
    except ClientError as e:
        error_code = e.response["Error"]["Code"]
        if error_code == "ResourceNotFoundException":
            raise ValueError(f"Target '{target_id}' not found on gateway '{gateway_id}'")
        else:
            raise

