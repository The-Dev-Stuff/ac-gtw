"""
manage_tools.py
Creates, updates, or deletes gateway targets (tools) on an AgentCore Gateway.
Handles OpenAPI schema management and credential provider configuration.
"""
import os
import boto3
from botocore.exceptions import ClientError

# CONFIG: change these as needed
AWS_REGION = os.environ.get("AWS_DEFAULT_REGION", "us-east-1")


def upload_openapi_to_s3(openapi_file_path: str, bucket_name: str = None):
    """
    Uploads an OpenAPI spec file to S3.

    Args:
        openapi_file_path: Path to the local OpenAPI JSON file
        bucket_name: Optional S3 bucket name. If not provided, uses default pattern.

    Returns:
        S3 URI of the uploaded file (s3://bucket/key)
    """
    session = boto3.Session(region_name=AWS_REGION)
    s3 = session.client("s3")
    sts = session.client("sts")

    # Get account ID for bucket naming if bucket not provided
    if not bucket_name:
        account_id = sts.get_caller_identity()["Account"]
        bucket_name = f"agentcore-gateway-targets-openapi-specs-{account_id}-{AWS_REGION}"

    # Ensure bucket exists
    print(f"Ensuring S3 bucket exists: {bucket_name}")
    try:
        if AWS_REGION == "us-east-1":
            s3.create_bucket(Bucket=bucket_name)
        else:
            s3.create_bucket(
                Bucket=bucket_name,
                CreateBucketConfiguration={"LocationConstraint": AWS_REGION}
            )
        print("✓ Created S3 bucket.")
    except ClientError as e:
        if e.response["Error"]["Code"] in ("BucketAlreadyOwnedByYou", "BucketAlreadyExists"):
            print("✓ S3 bucket already exists.")
        else:
            raise

    # Upload OpenAPI file
    object_key = os.path.basename(openapi_file_path)
    print(f"Uploading OpenAPI file to S3: {object_key}")
    with open(openapi_file_path, "rb") as f:
        s3.put_object(Bucket=bucket_name, Key=object_key, Body=f.read())
    print("✓ OpenAPI file uploaded.")

    s3_uri = f"s3://{bucket_name}/{object_key}"
    print(f"S3 URI: {s3_uri}")
    return s3_uri


def create_or_get_api_key_credential_provider(provider_name: str, api_key: str):
    """
    Creates or retrieves an API key credential provider.

    Args:
        provider_name: Name of the credential provider
        api_key: The API key value

    Returns:
        Credential provider ARN
    """
    session = boto3.Session(region_name=AWS_REGION)
    agentcore = session.client("bedrock-agentcore-control")

    print(f"Creating/retrieving credential provider: {provider_name}")
    try:
        resp = agentcore.create_api_key_credential_provider(
            name=provider_name,
            apiKey=api_key
        )
        credential_provider_arn = resp["credentialProviderArn"]
        print("✓ Credential provider created.")
    except ClientError as e:
        if "already exists" in str(e) or "EntityAlreadyExists" in str(e):
            print("✓ Credential provider already exists.")
            raise ValueError(
                f"Credential provider '{provider_name}' already exists. "
                "Please use a unique name or handle provider updates manually."
            )
        else:
            raise

    print(f"Credential provider ARN: {credential_provider_arn}")
    return credential_provider_arn


def create_gateway_target(
    gateway_id: str,
    target_name: str,
    openapi_s3_uri: str,
    api_key_credential_provider_arn: str,
    api_key_param_name: str = "api_key",
    api_key_location: str = "QUERY_PARAMETER",
    description: str = None
):
    """
    Creates a gateway target (tool) with OpenAPI spec and credential injection.
    OpenAPI schema targets require either OAUTH or API_KEY credential provider.

    Docs: https://docs.aws.amazon.com/bedrock-agentcore-control/latest/APIReference/API_CreateGatewayTarget.html

    Args:
        gateway_id: ID of the gateway
        target_name: Name of the target
        openapi_s3_uri: S3 URI of the OpenAPI spec
        api_key_credential_provider_arn: ARN of credential provider for API key injection (required)
        api_key_param_name: Parameter name for the API key (e.g., "api_key", "Authorization")
        api_key_location: Where to inject the key: "QUERY_PARAMETER" or "HEADER"
        description: Optional target description

    Returns:
        dict: Target creation response containing:
            - createdAt (str): Timestamp when the target was created
            - credentialProviderConfigurations (list): Credential provider configurations
            - description (str): Description of the target
            - gatewayArn (str): ARN of the gateway
            - lastSynchronizedAt (str): Last synchronization timestamp
            - name (str): Name of the target
            - status (str): Current status (CREATING, UPDATING, READY, FAILED, etc.)
            - statusReasons (list): Reasons for current status
            - targetConfiguration (dict): Configuration settings for the target
            - targetId (str): Unique identifier of the created target
            - updatedAt (str): Timestamp when target was last updated
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



def delete_gateway_target(gateway_id: str, target_id: str):
    """
    Deletes a gateway target (tool) from a gateway.
    Docs: https://docs.aws.amazon.com/bedrock-agentcore-control/latest/APIReference/API_DeleteGatewayTarget.html

    Args:
        gateway_id: The unique identifier of the gateway
        target_id: The unique identifier of the target to delete

    Returns:
        Delete response containing gatewayArn, status, statusReasons, targetId
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


def add_tool_to_gateway(
    gateway_id: str,
    target_name: str,
    openapi_file_path: str,
    api_key: str = None,
    api_key_provider_name: str = None,
    api_key_param_name: str = "api_key",
    api_key_location: str = "QUERY_PARAMETER",
    s3_bucket: str = None,
    description: str = None
):
    """
    Main entry point: adds a new tool (target) to a gateway.
    Handles OpenAPI upload to S3 and credential provider setup.

    Args:
        gateway_id: ID of the gateway
        target_name: Name of the target/tool
        openapi_file_path: Path to the OpenAPI spec file
        api_key: Optional API key for the external service
        api_key_provider_name: Optional name for the credential provider
        api_key_param_name: Parameter name for API key injection
        api_key_location: "QUERY_PARAMETER" or "HEADER"
        s3_bucket: Optional custom S3 bucket name
        description: Optional target description

    Returns:
        dict: Target creation response (HTTP 202) containing:
            - createdAt (str): Timestamp when the target was created
            - credentialProviderConfigurations (list): Array of CredentialProviderConfiguration
              objects containing credential provider details and type
            - description (str): Description of the target (1-200 chars)
            - gatewayArn (str): The Amazon Resource Name (ARN) of the gateway
            - lastSynchronizedAt (str): Last synchronization timestamp of the target
            - name (str): Name of the target (pattern: ([0-9a-zA-Z][-]?){1,100})
            - status (str): Current status. Valid values: CREATING, UPDATING,
              UPDATE_UNSUCCESSFUL, DELETING, READY, FAILED, SYNCHRONIZING,
              SYNCHRONIZE_UNSUCCESSFUL
            - statusReasons (list): Array of strings explaining current status (0-100 items)
            - targetConfiguration (dict): Configuration settings for the target (Union object)
            - targetId (str): Unique identifier of the created target (pattern: [0-9a-zA-Z]{10})
            - updatedAt (str): Timestamp when target was last updated
    """
    # Step 1: Upload OpenAPI spec to S3
    openapi_s3_uri = upload_openapi_to_s3(openapi_file_path, s3_bucket)

    # Step 2: Create credential provider
    # OpenAPI schema targets require either OAUTH or API_KEY - GATEWAY_IAM_ROLE is not supported
    if api_key and api_key_provider_name:
        # Use provided API key
        api_key_credential_provider_arn = create_or_get_api_key_credential_provider(
            api_key_provider_name,
            api_key
        )
    else:
        # For public APIs, create a placeholder API key credential provider
        # The placeholder key won't be used by the target API but satisfies AWS requirements
        placeholder_provider_name = f"{target_name}-placeholder-apikey"
        placeholder_api_key = "placeholder-not-used"
        api_key_credential_provider_arn = create_or_get_api_key_credential_provider(
            placeholder_provider_name,
            placeholder_api_key
        )
        # Use a header that won't interfere with the actual API
        api_key_param_name = "X-Placeholder-Auth"
        api_key_location = "HEADER"

    # Step 3: Create the gateway target
    response = create_gateway_target(
        gateway_id=gateway_id,
        target_name=target_name,
        openapi_s3_uri=openapi_s3_uri,
        api_key_credential_provider_arn=api_key_credential_provider_arn,
        api_key_param_name=api_key_param_name,
        api_key_location=api_key_location,
        description=description
    )

    return response


if __name__ == "__main__":
    print("To use this module, import it and call:")
    print("  from tools import add_tool_to_gateway")
    print("  response = add_tool_to_gateway(")
    print("      gateway_id='gw-xxx',")
    print("      target_name='MyTool',")
    print("      openapi_file_path='path/to/spec.json',")
    print("      api_key='your-api-key',")
    print("      api_key_provider_name='MyToolAPIKey'")
    print("  )")

