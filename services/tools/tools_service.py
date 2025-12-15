"""
tools_service.py
Gateway target (tool) creation and deletion.
Handles OpenAPI schema registration with credential injection.
"""
import os
import boto3
from botocore.exceptions import ClientError

AWS_REGION = os.environ.get("AWS_DEFAULT_REGION", "us-east-1")

def get_gateway_target(gateway_id: str, target_id: str) -> dict:
    """
    Retrieve information about a specific gateway target.

    Docs: https://docs.aws.amazon.com/bedrock-agentcore-control/latest/APIReference/API_GetGatewayTarget.html

    Args:
        gateway_id: The unique identifier of the gateway
        target_id: The unique identifier of the target to retrieve

    Returns:
        dict: Target details containing:
            - targetId (str): Unique identifier of the target
            - name (str): Name of the target
            - description (str): Description of the target
            - status (str): Current status (READY, CREATING, etc.)
            - gatewayArn (str): ARN of the gateway
            - createdAt (str): Creation timestamp
            - updatedAt (str): Last update timestamp
            - lastSynchronizedAt (str): Last synchronization timestamp
            - statusReasons (list): Reasons for current status
            - targetConfiguration (dict): Target configuration
            - credentialProviderConfigurations (list): Credential provider configurations

    Raises:
        ValueError: If target not found on gateway
        ClientError: If AWS API call fails
    """
    session = boto3.Session(region_name=AWS_REGION)
    gateway_client = session.client("bedrock-agentcore-control")

    print(f"Retrieving gateway target: {target_id} from gateway: {gateway_id}...")

    try:
        response = gateway_client.get_gateway_target(
            gatewayIdentifier=gateway_id,
            targetId=target_id
        )
        print(f"✓ Gateway target retrieved. Name: {response.get('name')}")
        return response
    except ClientError as e:
        error_code = e.response["Error"]["Code"]
        if error_code == "ResourceNotFoundException":
            raise ValueError(f"Target '{target_id}' not found on gateway '{gateway_id}'")
        else:
            raise


def list_gateway_targets(gateway_id: str, max_results: int = None, next_token: str = None) -> dict:
    """
    List all targets for a specific gateway.

    Docs: https://docs.aws.amazon.com/bedrock-agentcore-control/latest/APIReference/API_ListGatewayTargets.html

    Args:
        gateway_id: The unique identifier of the gateway
        max_results: Maximum number of results to return (1-1000). If not provided, uses AWS default.
        next_token: Token for pagination to get the next batch of results

    Returns:
        dict: Contains:
            - items (list): Array of target summary objects with:
                - targetId, name, description, status, createdAt, updatedAt
            - nextToken (str): Token for pagination if more results available

    Raises:
        ValueError: If parameters are invalid
        ClientError: If AWS API call fails
    """
    session = boto3.Session(region_name=AWS_REGION)
    gateway_client = session.client("bedrock-agentcore-control")

    print(f"Listing all targets for gateway: {gateway_id}...")

    list_params = {"gatewayIdentifier": gateway_id}

    if max_results is not None:
        if max_results < 1 or max_results > 1000:
            raise ValueError("maxResults must be between 1 and 1000")
        list_params["maxResults"] = max_results

    if next_token is not None:
        list_params["nextToken"] = next_token

    try:
        response = gateway_client.list_gateway_targets(**list_params)
        items = response.get("items", [])
        print(f"✓ Retrieved {len(items)} target(s).")
        if response.get("nextToken"):
            print(f"  More results available. Use nextToken to fetch more.")
        return response
    except ClientError as e:
        raise


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
    Create a gateways target (tool) with OpenAPI spec and credential injection.

    OpenAPI schema targets require either OAUTH or API_KEY credential provider.

    Docs: https://docs.aws.amazon.com/bedrock-agentcore-control/latest/APIReference/API_CreateGatewayTarget.html

    Args:
        gateway_id: ID of the gateways
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
            - gatewayArn (str): ARN of the gateways
            - description (str): Description of the target
            - createdAt (str): Timestamp when the target was created
            - updatedAt (str): Timestamp when target was last updated
            - lastSynchronizedAt (str): Last synchronization timestamp
            - statusReasons (list): Reasons for current status
            - targetConfiguration (dict): Configuration settings for the target
            - credentialProviderConfigurations (list): Credential provider configurations

    Raises:
        ValueError: If target name already exists on the gateways
        ClientError: If AWS API call fails
    """
    session = boto3.Session(region_name=AWS_REGION)
    gateway_client = session.client("bedrock-agentcore-control")

    print(f"Creating gateways target: {target_name}")

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
            print("✗ Target name already exists for this gateways.")
            raise ValueError(f"Target '{target_name}' already exists on gateways {gateway_id}")
        else:
            raise


def update_gateway_target(
    gateway_id: str,
    target_id: str,
    target_name: str,
    target_configuration: dict,
    description: str = None,
    credential_provider_configurations: list = None
) -> dict:
    """
    Update an existing gateways target (tool).

    Docs: https://docs.aws.amazon.com/bedrock-agentcore-control/latest/APIReference/API_UpdateGatewayTarget.html

    Args:
        gateway_id: The unique identifier of the gateways
        target_id: The unique identifier of the target to update
        target_name: The updated name for the gateways target
        target_configuration: The updated target configuration (e.g., mcp with openApiSchema)
        description: Optional updated description
        credential_provider_configurations: Optional updated credential provider configurations

    Returns:
        dict: Update response containing:
            - targetId (str): ID of the updated target
            - name (str): Updated name
            - status (str): Current status (UPDATING, READY, etc.)
            - gatewayArn (str): ARN of the gateways
            - description (str): Updated description
            - createdAt (str): Original creation timestamp
            - updatedAt (str): Timestamp of last update
            - lastSynchronizedAt (str): Last synchronization timestamp
            - statusReasons (list): Reasons for current status
            - targetConfiguration (dict): Updated configuration
            - credentialProviderConfigurations (list): Updated credential provider configurations

    Raises:
        ValueError: If target not found on gateways
        ClientError: If AWS API call fails
    """
    session = boto3.Session(region_name=AWS_REGION)
    gateway_client = session.client("bedrock-agentcore-control")

    print(f"Updating gateways target: {target_id} on gateways: {gateway_id}")

    # Fetch existing target to preserve S3 URI and credentials if not provided
    existing_target = None
    try:
        existing_target = get_gateway_target(gateway_id, target_id)
    except Exception as e:
        print(f"Warning: Could not fetch existing target: {str(e)}")

    # If target_configuration not provided, use existing
    if target_configuration is None:
        if existing_target:
            target_configuration = existing_target.get("targetConfiguration")
            print(f"No target configuration provided. Using existing configuration.")
        else:
            raise ValueError(f"target_configuration is required when updating tool if existing target cannot be retrieved")

    # Build update parameters
    update_params = {
        "gatewayIdentifier": gateway_id,
        "targetId": target_id,
        "name": target_name,
        "targetConfiguration": target_configuration
    }

    # If target_configuration has an empty S3 URI, preserve existing one
    if existing_target and target_configuration:
        # Check if S3 URI is provided in the new configuration
        existing_s3_uri = None
        if existing_target.get("targetConfiguration"):
            existing_s3_uri = (
                existing_target.get("targetConfiguration", {})
                .get("mcp", {})
                .get("openApiSchema", {})
                .get("s3", {})
                .get("uri")
            )

        new_s3_uri = (
            target_configuration.get("mcp", {})
            .get("openApiSchema", {})
            .get("s3", {})
            .get("uri")
        )

        # If no S3 URI provided in new config but one exists, use the existing URI
        if not new_s3_uri and existing_s3_uri:
            print(f"No S3 URI provided in update. Using existing S3 URI: {existing_s3_uri}")
            target_configuration["mcp"]["openApiSchema"]["s3"]["uri"] = existing_s3_uri
            update_params["targetConfiguration"] = target_configuration

    # Add credential configurations if provided
    # If not provided, fetch existing credentials from the target
    if credential_provider_configurations is not None:
        update_params["credentialProviderConfigurations"] = credential_provider_configurations
    elif existing_target:
        # Use existing credentials if not provided
        existing_creds = existing_target.get("credentialProviderConfigurations")
        if existing_creds:
            update_params["credentialProviderConfigurations"] = existing_creds
            print(f"Using existing credential configurations from current target")

    # Add optional parameters if provided
    if description is not None:
        update_params["description"] = description

    print(f"Update params: {update_params}")

    try:
        response = gateway_client.update_gateway_target(**update_params)
        print("✓ Gateway target updated.")

        # Log key response details
        print(f"  Target ID: {response.get('targetId')}")
        print(f"  Gateway ARN: {response.get('gatewayArn')}")
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
            raise ValueError(f"Target '{target_id}' not found on gateways '{gateway_id}'")
        else:
            raise


def delete_gateway_target(gateway_id: str, target_id: str) -> dict:
    """
    Delete a gateways target (tool) from a gateways.

    Docs: https://docs.aws.amazon.com/bedrock-agentcore-control/latest/APIReference/API_DeleteGatewayTarget.html

    Args:
        gateway_id: The unique identifier of the gateways
        target_id: The unique identifier of the target to delete

    Returns:
        dict: Deletion response containing:
            - targetId (str): ID of the deleted target
            - gatewayArn (str): ARN of the gateways
            - status (str): Current status (DELETING, etc.)
            - statusReasons (list): Reasons for current status

    Raises:
        ValueError: If target not found on gateways
        ClientError: If AWS API call fails
    """
    session = boto3.Session(region_name=AWS_REGION)
    gateway_client = session.client("bedrock-agentcore-control")

    print(f"Deleting gateways target: {target_id} from gateways: {gateway_id}")

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
            raise ValueError(f"Target '{target_id}' not found on gateways '{gateway_id}'")
        else:
            raise

