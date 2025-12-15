"""
main.py
FastAPI application for managing gateways tools.
"""
import os
import sys
import json
from pathlib import Path
import requests

# Add parent directory to path for direct execution
sys.path.insert(0, str(Path(__file__).parent.parent))

from fastapi import FastAPI, UploadFile, File, Form, HTTPException, status, Body

from services.gateways.gateway_service import create_agentcore_gateway_role, create_gateway as create_gateway_service, update_gateway as update_gateway_service, get_gateway as get_gateway_service, list_gateways as list_gateways_service, delete_gateway as delete_gateway_service
from services.s3.s3_service import upload_openapi_spec
from services.tools.tools_service import create_gateway_target, update_gateway_target, delete_gateway_target, get_gateway_target, list_gateway_targets
from services.credentials.credentials_service import create_or_get_api_key_credential_provider
from services.openapi_generator.openapi_generator import generate_openapi_spec
from api.models import HealthCheckResponse, CreateToolResponse, CreateGatewayRequest, CreateGatewayNoAuthRequest, CreateGatewayResponse, UpdateGatewayRequest, UpdateGatewayResponse, GetGatewayResponse, ListGatewaysResponse, GatewaySummary, Auth, CreateToolFromUrlRequest, CreateToolFromApiInfoRequest, CreateToolFromSpecRequest, UpdateToolResponse, UpdateToolRequest, GetGatewayTargetResponse, ListGatewayTargetsResponse, TargetSummary, DeleteToolResponse, DeleteGatewayResponse
from api.validations import validate_auth

# CONFIG
AWS_REGION = os.environ.get("AWS_DEFAULT_REGION", "us-east-1")
OPENAPI_SPECS_BUCKET = os.environ.get("OPENAPI_SPECS_BUCKET", "agentcore-gateway-openapi-specs-bucket")

# Create FastAPI app
app = FastAPI(
    title="AgentCore Gateway Tools API",
    description="API for managing OpenAPI tools on AgentCore Gateway",
    version="1.0.0"
)


def _register_tool_with_gateway(
    gateway_id: str,
    target_name: str,
    openapi_s3_uri: str,
    auth: Auth = None,
    description: str = None
) -> dict:
    """
    Register a tool with a gateways by creating credential provider and target.

    This is the orchestration logic for the API layer.
    If auth is provided with api_key, uses real credentials.
    Otherwise, creates placeholder credentials for public APIs.

    Args:
        gateway_id: ID of the gateways
        target_name: Name of the target/tool
        openapi_s3_uri: S3 URI of the OpenAPI spec
        auth: Optional Auth object with api_key credentials
        description: Optional target description

    Returns:
        dict: Target creation response from AWS
    """
    # Determine credential values based on auth object
    if auth and auth.type == "api_key":
        # Use provided API key credentials
        api_key = auth.config.api_key
        api_key_provider_name = auth.provider_name
        api_key_param_name = auth.config.api_key_param_name
        api_key_location = auth.config.api_key_location
    else:
        # For public APIs, use placeholder credentials
        api_key = "placeholder-not-used"
        api_key_provider_name = f"{target_name}-placeholder-apikey"
        api_key_param_name = "X-Placeholder-Auth"
        api_key_location = "HEADER"

    # Create credential provider
    api_key_credential_provider_arn = create_or_get_api_key_credential_provider(
        api_key_provider_name,
        api_key
    )

    # Create gateways target
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


@app.get("/health", response_model=HealthCheckResponse)
async def health_check():
    """Health check endpoint"""
    return HealthCheckResponse(
        status="healthy",
        message="AgentCore Gateway Tools API is running",
        openapi_specs_bucket=OPENAPI_SPECS_BUCKET,
        aws_region=AWS_REGION
    )

## Gateways / MCP Servers

# Retrieves a specific gateway
@app.get("/gateways/{gateway_id}", response_model=GetGatewayResponse)
async def get_gateway(gateway_id: str):
    """
    Retrieve information about a specific gateway.

    Args:
        gateway_id: The unique identifier of the gateway

    Returns:
        GetGatewayResponse with full gateway details
    """
    try:
        response = get_gateway_service(gateway_id=gateway_id)

        return GetGatewayResponse(
            status="success",
            message=f"Gateway '{response.get('name')}' retrieved successfully",
            # AWS SDK response fields
            gateway_id=response.get("gatewayId"),
            gateway_url=response.get("gatewayUrl"),
            gateway_arn=response.get("gatewayArn"),
            name=response.get("name"),
            description=response.get("description"),
            created_at=response.get("createdAt"),
            updated_at=response.get("updatedAt"),
            gateway_status=response.get("status"),
            status_reasons=response.get("statusReasons"),
            authorizer_type=response.get("authorizerType"),
            protocol_type=response.get("protocolType"),
            role_arn=response.get("roleArn"),
            authorizer_configuration=response.get("authorizerConfiguration"),
            protocol_configuration=response.get("protocolConfiguration"),
            exception_level=response.get("exceptionLevel"),
            interceptor_configurations=response.get("interceptorConfigurations"),
            policy_engine_configuration=response.get("policyEngineConfiguration"),
            kms_key_arn=response.get("kmsKeyArn"),
            workload_identity_details=response.get("workloadIdentityDetails")
        )

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except Exception as e:
        print(f"Error retrieving gateway: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve gateway: {str(e)}"
        )

# Lists all gateways
@app.get("/gateways", response_model=ListGatewaysResponse)
async def list_gateways(max_results: int = None, next_token: str = None):
    """
    List all gateways in the account.

    Args:
        max_results: Maximum number of results to return (1-1000). Default uses AWS default.
        next_token: Token for pagination to get the next batch of results

    Returns:
        ListGatewaysResponse with gateway summaries and pagination token
    """
    try:
        # Validate max_results if provided
        if max_results is not None:
            if max_results < 1 or max_results > 1000:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="maxResults must be between 1 and 1000"
                )

        response = list_gateways_service(max_results=max_results, next_token=next_token)

        # Transform items to match GatewaySummary model
        items = [
            GatewaySummary(
                gateway_id=item.get("gatewayId"),
                name=item.get("name"),
                description=item.get("description"),
                gateway_status=item.get("status"),
                authorizer_type=item.get("authorizerType"),
                protocol_type=item.get("protocolType"),
                created_at=item.get("createdAt"),
                updated_at=item.get("updatedAt")
            )
            for item in response.get("items", [])
        ]

        return ListGatewaysResponse(
            status="success",
            message=f"Retrieved {len(items)} gateway(s)",
            items=items,
            next_token=response.get("nextToken")
        )

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error listing gateways: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list gateways: {str(e)}"
        )

@app.post("/gateways", response_model=CreateGatewayResponse)
async def create_gateway(request: CreateGatewayRequest):
    """Create a new gateways with provided authentication configuration"""
    try:
        # Validate required auth config
        required_keys = ["client_id", "discovery_url"]
        for key in required_keys:
            if key not in request.auth_config.__dict__ or not getattr(request.auth_config, key):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Missing required auth_config field: {key}"
                )

        # Create IAM role
        role_arn = create_agentcore_gateway_role("sample-lambdagateway-role-demo")

        # Create or get gateways with JWT auth
        auth_config = {
            "client_id": request.auth_config.client_id,
            "discovery_url": request.auth_config.discovery_url,
        }
        
        gateway_info = create_gateway_service(
            gateway_name=request.gateway_name,
            role_arn=role_arn,
            is_authenticated=True,
            auth_config=auth_config,
            description=request.description
        )

        return CreateGatewayResponse(
            status="success",
            message=f"Gateway '{request.gateway_name}' successfully created",
            # AWS SDK response fields
            gateway_id=gateway_info.get("gatewayId"),
            gateway_url=gateway_info.get("gatewayUrl"),
            gateway_arn=gateway_info.get("gatewayArn"),
            name=gateway_info.get("name"),
            description=gateway_info.get("description"),
            created_at=gateway_info.get("createdAt"),
            updated_at=gateway_info.get("updatedAt"),
            gateway_status=gateway_info.get("status"),
            status_reasons=gateway_info.get("statusReasons"),
            authorizer_type=gateway_info.get("authorizerType"),
            protocol_type=gateway_info.get("protocolType"),
            role_arn=gateway_info.get("roleArn"),
            authorizer_configuration=gateway_info.get("authorizerConfiguration"),
            protocol_configuration=gateway_info.get("protocolConfiguration"),
            exception_level=gateway_info.get("exceptionLevel"),
            interceptor_configurations=gateway_info.get("interceptorConfigurations"),
            policy_engine_configuration=gateway_info.get("policyEngineConfiguration"),
            kms_key_arn=gateway_info.get("kmsKeyArn"),
            workload_identity_details=gateway_info.get("workloadIdentityDetails")
        )

    except HTTPException:
        raise
    except Exception as e:
        print(f"Error creating gateways: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create gateways: {str(e)}"
        )


@app.post("/gateways/no-auth", response_model=CreateGatewayResponse)
async def create_gateway_no_auth(request: CreateGatewayNoAuthRequest):
    """Create a new gateways without authentication"""
    try:
        # Create IAM role
        role_arn = create_agentcore_gateway_role("sample-lambdagateway-role-demo")

        # Create or get gateways without auth
        gateway_info = create_gateway_service(
            gateway_name=request.gateway_name,
            role_arn=role_arn,
            is_authenticated=False,
            description=request.description
        )

        return CreateGatewayResponse(
            status="success",
            message=f"Gateway '{request.gateway_name}' successfully created without authentication",
            # AWS SDK response fields
            gateway_id=gateway_info.get("gatewayId"),
            gateway_url=gateway_info.get("gatewayUrl"),
            gateway_arn=gateway_info.get("gatewayArn"),
            name=gateway_info.get("name"),
            description=gateway_info.get("description"),
            created_at=gateway_info.get("createdAt"),
            updated_at=gateway_info.get("updatedAt"),
            gateway_status=gateway_info.get("status"),
            status_reasons=gateway_info.get("statusReasons"),
            authorizer_type=gateway_info.get("authorizerType"),
            protocol_type=gateway_info.get("protocolType"),
            role_arn=gateway_info.get("roleArn"),
            authorizer_configuration=gateway_info.get("authorizerConfiguration"),
            protocol_configuration=gateway_info.get("protocolConfiguration"),
            exception_level=gateway_info.get("exceptionLevel"),
            interceptor_configurations=gateway_info.get("interceptorConfigurations"),
            policy_engine_configuration=gateway_info.get("policyEngineConfiguration"),
            kms_key_arn=gateway_info.get("kmsKeyArn"),
            workload_identity_details=gateway_info.get("workloadIdentityDetails")
        )

    except HTTPException:
        raise
    except Exception as e:
        print(f"Error creating gateways (no auth): {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create gateways: {str(e)}"
        )


# Updates an existing gateway
@app.put("/gateways/{gateway_id}", response_model=UpdateGatewayResponse)
async def update_gateway(gateway_id: str, request: UpdateGatewayRequest):
    """Update an existing gateway"""
    try:
        name = request.name
        protocol_type = request.protocol_type
        authorizer_type = request.authorizer_type
        role_arn = request.role_arn
        description = request.description

        # Validate required parameters
        if authorizer_type not in ["CUSTOM_JWT", "AWS_IAM", "NONE"]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="authorizer_type must be one of: CUSTOM_JWT, AWS_IAM, NONE"
            )

        if protocol_type != "MCP":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="protocol_type must be MCP"
            )

        response = update_gateway_service(
            gateway_id=gateway_id,
            name=name,
            protocol_type=protocol_type,
            authorizer_type=authorizer_type,
            role_arn=role_arn,
            description=description
        )

        return UpdateGatewayResponse(
            status="success",
            message=f"Gateway '{name}' successfully updated",
            # AWS SDK response fields
            gateway_id=response.get("gatewayId"),
            gateway_url=response.get("gatewayUrl"),
            gateway_arn=response.get("gatewayArn"),
            name=response.get("name"),
            description=response.get("description"),
            created_at=response.get("createdAt"),
            updated_at=response.get("updatedAt"),
            gateway_status=response.get("status"),
            status_reasons=response.get("statusReasons"),
            authorizer_type=response.get("authorizerType"),
            protocol_type=response.get("protocolType"),
            role_arn=response.get("roleArn"),
            authorizer_configuration=response.get("authorizerConfiguration"),
            protocol_configuration=response.get("protocolConfiguration"),
            exception_level=response.get("exceptionLevel"),
            interceptor_configurations=response.get("interceptorConfigurations"),
            policy_engine_configuration=response.get("policyEngineConfiguration"),
            kms_key_arn=response.get("kmsKeyArn"),
            workload_identity_details=response.get("workloadIdentityDetails")
        )

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error updating gateway: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update gateway: {str(e)}"
        )


# Deletes an existing gateway
@app.delete("/gateways/{gateway_id}", response_model=DeleteGatewayResponse, status_code=status.HTTP_202_ACCEPTED)
async def delete_gateway(gateway_id: str):
    """Delete an existing gateway"""
    try:
        delete_gateway_service(gateway_id=gateway_id)

        return DeleteGatewayResponse(
            gateway_id=gateway_id,
            status="DELETING"
        )
    except Exception as e:
        print(f"Error deleting gateway: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete gateway: {str(e)}"
        )

## Tools

# Retrieves a specific gateway tool (target)
@app.get("/gateways/{gateway_id}/tools/{target_id}", response_model=GetGatewayTargetResponse)
async def get_tool(gateway_id: str, target_id: str):
    """
    Retrieve information about a specific gateway target (tool).

    Args:
        gateway_id: The unique identifier of the gateway
        target_id: The unique identifier of the target

    Returns:
        GetGatewayTargetResponse with full target details
    """
    try:
        response = get_gateway_target(gateway_id=gateway_id, target_id=target_id)

        return GetGatewayTargetResponse(
            status="success",
            message=f"Gateway target '{response.get('name')}' retrieved successfully",
            # AWS SDK response fields
            target_id=response.get("targetId"),
            name=response.get("name"),
            description=response.get("description"),
            gateway_arn=response.get("gatewayArn"),
            created_at=response.get("createdAt"),
            updated_at=response.get("updatedAt"),
            last_synchronized_at=response.get("lastSynchronizedAt"),
            target_status=response.get("status"),
            status_reasons=response.get("statusReasons"),
            target_configuration=response.get("targetConfiguration"),
            credential_provider_configurations=response.get("credentialProviderConfigurations")
        )

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except Exception as e:
        print(f"Error retrieving gateway target: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve gateway target: {str(e)}"
        )


# Lists all gateway targets (tools) for a gateway
@app.get("/gateways/{gateway_id}/tools", response_model=ListGatewayTargetsResponse)
async def list_tools(gateway_id: str, max_results: int = None, next_token: str = None):
    """
    List all targets (tools) for a specific gateway.

    Args:
        gateway_id: The unique identifier of the gateway
        max_results: Maximum number of results to return (1-1000). Default uses AWS default.
        next_token: Token for pagination to get the next batch of results

    Returns:
        ListGatewayTargetsResponse with target summaries and pagination token
    """
    try:
        # Validate max_results if provided
        if max_results is not None:
            if max_results < 1 or max_results > 1000:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="maxResults must be between 1 and 1000"
                )

        response = list_gateway_targets(gateway_id=gateway_id, max_results=max_results, next_token=next_token)

        # Transform items to TargetSummary objects
        items = [
            TargetSummary(
                target_id=item.get("targetId"),
                name=item.get("name"),
                description=item.get("description"),
                target_status=item.get("status"),
                created_at=item.get("createdAt"),
                updated_at=item.get("updatedAt")
            )
            for item in response.get("items", [])
        ]

        return ListGatewayTargetsResponse(
            status="success",
            message=f"Retrieved {len(items)} target(s)",
            items=items,
            next_token=response.get("nextToken")
        )

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error listing gateway targets: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list gateway targets: {str(e)}"
        )


# Creates tool from uploaded OpenAPI spec file
@app.post("/tools", response_model=CreateToolResponse)
async def create_tool(
    gateway_id: str = Form(...),
    tool_name: str = Form(...),
    openapi_spec_file: UploadFile = File(...),
    auth: str = Form(...),  # JSON string of Auth object
):
    """Create a new tool on the gateways"""
    try:
        # Parse auth JSON
        import json as json_module
        auth_obj: Auth = Auth.model_validate(json_module.loads(auth))

        # Validate auth configuration
        validate_auth(auth_obj)

        # Validate OpenAPI spec file
        if not openapi_spec_file.filename:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="OpenAPI spec file is required"
            )

        if not openapi_spec_file.filename.endswith(".json"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="OpenAPI spec file must be a JSON file"
            )

        # Read and validate OpenAPI spec
        spec_content = await openapi_spec_file.read()
        try:
            spec_json = json.loads(spec_content)
        except json.JSONDecodeError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid JSON in OpenAPI spec file"
            )

        # Basic OpenAPI validation
        if "openapi" not in spec_json and "swagger" not in spec_json:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="OpenAPI spec must contain 'openapi' or 'swagger' field"
            )

        # Upload OpenAPI spec to S3 directly (in-memory)
        s3_uri = upload_openapi_spec(spec_json, tool_name, gateway_id, bucket_name=OPENAPI_SPECS_BUCKET)

        # Register tool with gateways
        result = _register_tool_with_gateway(
            gateway_id=gateway_id,
            target_name=tool_name,
            openapi_s3_uri=s3_uri,
            auth=auth_obj,
            description=None
        )

        return CreateToolResponse(
            status="success",
            tool_name=tool_name,
            gateway_id=gateway_id,
            openapi_spec_path=str(s3_uri),
            message=f"Tool '{tool_name}' successfully created and registered on gateways {gateway_id}",
            # AWS SDK response fields
            target_id=result.get("targetId"),
            gateway_arn=result.get("gatewayArn"),
            description=result.get("description"),
            created_at=result.get("createdAt"),
            updated_at=result.get("updatedAt"),
            last_synchronized_at=result.get("lastSynchronizedAt"),
            target_status=result.get("status"),
            status_reasons=result.get("statusReasons"),
            target_configuration=result.get("targetConfiguration"),
            credential_provider_configurations=result.get("credentialProviderConfigurations")
        )

    except HTTPException:
        raise
    except Exception as e:
        print(f"Error creating tool: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create tool: {str(e)}"
        )


# Creates tool from uploaded OpenAPI spec file url
@app.post("/tools/from-url", response_model=CreateToolResponse)
async def create_tool_from_url(request: CreateToolFromUrlRequest):
    """Create a new tool on the gateways from an OpenAPI spec URL"""
    try:
        # Validate auth configuration
        validate_auth(request.auth)

        # Download OpenAPI spec from URL
        print(f"Downloading OpenAPI spec from {request.openapi_spec_url}")
        response = requests.get(request.openapi_spec_url, timeout=10)
        response.raise_for_status()

        try:
            spec_json = response.json()
        except json.JSONDecodeError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid JSON in OpenAPI spec from URL"
            )

        # Validate OpenAPI spec
        if "openapi" not in spec_json and "swagger" not in spec_json:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="OpenAPI spec must contain 'openapi' or 'swagger' field"
            )

        # Upload to S3 and register tool with gateways
        s3_uri = upload_openapi_spec(spec_json, request.tool_name, request.gateway_id, bucket_name=OPENAPI_SPECS_BUCKET)

        # Register tool with gateways
        result = _register_tool_with_gateway(
            gateway_id=request.gateway_id,
            target_name=request.tool_name,
            openapi_s3_uri=s3_uri,
            auth=request.auth,
            description=None
        )

        return CreateToolResponse(
            status="success",
            tool_name=request.tool_name,
            gateway_id=request.gateway_id,
            openapi_spec_path=str(s3_uri),
            message=f"Tool '{request.tool_name}' successfully created and registered on gateways {request.gateway_id}",
            # AWS SDK response fields
            target_id=result.get("targetId"),
            gateway_arn=result.get("gatewayArn"),
            description=result.get("description"),
            created_at=result.get("createdAt"),
            updated_at=result.get("updatedAt"),
            last_synchronized_at=result.get("lastSynchronizedAt"),
            target_status=result.get("status"),
            status_reasons=result.get("statusReasons"),
            target_configuration=result.get("targetConfiguration"),
            credential_provider_configurations=result.get("credentialProviderConfigurations")
        )

    except HTTPException:
        raise
    except requests.RequestException as e:
        print(f"Error downloading OpenAPI spec: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to download OpenAPI spec from URL: {str(e)}"
        )
    except Exception as e:
        print(f"Error creating tool from URL: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create tool: {str(e)}"
        )


# Creates tool from minimal API info. (System creates an OpenAPI spec on the fly)
@app.post("/tools/from-api-info", response_model=CreateToolResponse)
async def create_tool_from_api_info(request: CreateToolFromApiInfoRequest):
    """Create a new tool on the gateways from manual API information"""
    try:
        # Validate auth configuration
        validate_auth(request.auth)

        # Generate OpenAPI spec from API info
        spec_json = generate_openapi_spec(
            tool_name=request.tool_name,
            method=request.api_info.method,
            url=request.api_info.url,
            query_params=request.api_info.query_params,
            headers=request.api_info.headers,
            body_schema=request.api_info.body_schema,
            description=request.api_info.description
        )

        # Upload generated spec to S3
        s3_uri = upload_openapi_spec(spec_json, request.tool_name, request.gateway_id, bucket_name=OPENAPI_SPECS_BUCKET)

        # Register tool with gateways
        result = _register_tool_with_gateway(
            gateway_id=request.gateway_id,
            target_name=request.tool_name,
            openapi_s3_uri=s3_uri,
            auth=request.auth,
            description=request.api_info.description
        )

        return CreateToolResponse(
            status="success",
            tool_name=request.tool_name,
            gateway_id=request.gateway_id,
            openapi_spec_path=str(s3_uri),
            message=f"Tool '{request.tool_name}' successfully created and registered on gateways {request.gateway_id}",
            # AWS SDK response fields
            target_id=result.get("targetId"),
            gateway_arn=result.get("gatewayArn"),
            description=result.get("description"),
            created_at=result.get("createdAt"),
            updated_at=result.get("updatedAt"),
            last_synchronized_at=result.get("lastSynchronizedAt"),
            target_status=result.get("status"),
            status_reasons=result.get("statusReasons"),
            target_configuration=result.get("targetConfiguration"),
            credential_provider_configurations=result.get("credentialProviderConfigurations")
        )

    except HTTPException:
        raise
    except Exception as e:
        print(f"Error creating tool from API info: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create tool: {str(e)}"
        )


# Creates tool from JSON OpenAPI spec in payload
@app.post("/tools/from-spec", response_model=CreateToolResponse)
async def create_tool_from_spec(request: CreateToolFromSpecRequest):
    """Create a new tool on the gateways from an inline OpenAPI spec definition"""
    try:
        # Validate auth configuration
        validate_auth(request.auth)

        spec_json = request.openapi_spec

        # Validate OpenAPI spec
        if "openapi" not in spec_json and "swagger" not in spec_json:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="OpenAPI spec must contain 'openapi' or 'swagger' field"
            )

        # Upload the inline spec to S3
        s3_uri = upload_openapi_spec(spec_json, request.tool_name, request.gateway_id, bucket_name=OPENAPI_SPECS_BUCKET)

        # Register tool with gateways
        result = _register_tool_with_gateway(
            gateway_id=request.gateway_id,
            target_name=request.tool_name,
            openapi_s3_uri=s3_uri,
            auth=request.auth,
            description=None
        )

        return CreateToolResponse(
            status="success",
            tool_name=request.tool_name,
            gateway_id=request.gateway_id,
            openapi_spec_path=str(s3_uri),
            message=f"Tool '{request.tool_name}' successfully created and registered on gateways {request.gateway_id}",
            # AWS SDK response fields
            target_id=result.get("targetId"),
            gateway_arn=result.get("gatewayArn"),
            description=result.get("description"),
            created_at=result.get("createdAt"),
            updated_at=result.get("updatedAt"),
            last_synchronized_at=result.get("lastSynchronizedAt"),
            target_status=result.get("status"),
            status_reasons=result.get("statusReasons"),
            target_configuration=result.get("targetConfiguration"),
            credential_provider_configurations=result.get("credentialProviderConfigurations")
        )

    except HTTPException:
        raise
    except Exception as e:
        print(f"Error creating tool from spec: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create tool: {str(e)}"
        )


# Updates tool (target) on gateways
@app.put("/gateways/{gateway_id}/tools/{target_id}", response_model=UpdateToolResponse)
async def update_tool(
    gateway_id: str,
    target_id: str,
    request: UpdateToolRequest
):
    """
    Update a tool (target) on a gateways.

    Args:
        gateway_id: The unique identifier of the gateways
        target_id: The unique identifier of the target to update
        request: UpdateToolRequest containing:
            - target_name (required): The updated name for the tool
            - target_configuration (required): The updated target configuration (with mcp.openApiSchema.s3.uri)
            - credential_provider_configurations (optional): Only required if updating credentials or for authenticated gateways
            - description (optional): Updated description for the tool

    Returns:
        UpdateToolResponse with update status and details

    Note:
        For gateways without authentication, credential_provider_configurations can be omitted.
        The service will automatically preserve existing credential configurations if not provided.
    """
    try:
        response = update_gateway_target(
            gateway_id=gateway_id,
            target_id=target_id,
            target_name=request.target_name,
            target_configuration=request.target_configuration,
            credential_provider_configurations=request.credential_provider_configurations,
            description=request.description
        )

        return UpdateToolResponse(
            status="success",
            tool_name=request.target_name,
            target_id=response.get("targetId", target_id),
            gateway_id=gateway_id,
            message=f"Tool '{request.target_name}' (target {target_id}) successfully updated on gateways '{gateway_id}'",
            # AWS SDK response fields
            gateway_arn=response.get("gatewayArn"),
            description=response.get("description"),
            created_at=response.get("createdAt"),
            updated_at=response.get("updatedAt"),
            last_synchronized_at=response.get("lastSynchronizedAt"),
            target_status=response.get("status"),
            status_reasons=response.get("statusReasons"),
            target_configuration=response.get("targetConfiguration"),
            credential_provider_configurations=response.get("credentialProviderConfigurations")
        )

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except Exception as e:
        print(f"Error updating tool: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update tool: {str(e)}"
        )


# Deletes tool (target) from gateway - A target can be 1 tool or multiple tools
@app.delete("/gateways/{gateway_id}/tools/{target_id}", response_model=DeleteToolResponse)
async def delete_tool(gateway_id: str, target_id: str):
    """
    Delete a tool (target) from a gateways.

    Args:
        gateway_id: The unique identifier of the gateways
        target_id: The unique identifier of the target to delete

    Returns:
        DeleteToolResponse with deletion status
    """
    try:
        response = delete_gateway_target(
            gateway_id=gateway_id,
            target_id=target_id
        )

        return DeleteToolResponse(
            status=response.get("status", "DELETING"),
            target_id=response.get("targetId", target_id),
            gateway_id=gateway_id,
            gateway_arn=response.get("gatewayArn"),
            status_reasons=response.get("statusReasons"),
            message=f"Tool '{target_id}' deletion initiated on gateways '{gateway_id}'"
        )

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except Exception as e:
        print(f"Error deleting tool: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete tool: {str(e)}"
        )


if __name__ == "__main__":
    import uvicorn

    print("Starting AgentCore Gateway Tools API...")
    print(f"OpenAPI specs bucket: {OPENAPI_SPECS_BUCKET}")
    print(f"AWS Region: {AWS_REGION}")

    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8000,
        log_level="info"
    )
