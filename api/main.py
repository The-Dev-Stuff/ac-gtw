"""
main.py
FastAPI application for managing gateway tools.
"""
import os
import sys
import json
from pathlib import Path
import requests

# Add parent directory to path for direct execution
sys.path.insert(0, str(Path(__file__).parent.parent))

from fastapi import FastAPI, UploadFile, File, Form, HTTPException, status

from services.gateway.gateway_service import create_agentcore_gateway_role, create_gateway
from services.s3.s3_service import upload_openapi_spec
from services.tools.tools_service import create_gateway_target, delete_gateway_target
from services.credentials.credentials_service import create_or_get_api_key_credential_provider
from services.openapi_generator.openapi_generator import generate_openapi_spec
from api.models import HealthCheckResponse, CreateToolResponse, CreateGatewayRequest, CreateGatewayNoAuthRequest, CreateGatewayResponse, Auth, CreateToolFromUrlRequest, CreateToolFromApiInfoRequest, CreateToolFromSpecRequest, DeleteToolResponse
from api.validations import validate_auth

# CONFIG
AWS_REGION = os.environ.get("AWS_DEFAULT_REGION", "us-east-1")
OPENAPI_SPECS_BUCKET = os.environ.get("OPENAPI_SPECS_BUCKET")

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
    Register a tool with a gateway by creating credential provider and target.

    This is the orchestration logic for the API layer.
    If auth is provided with api_key, uses real credentials.
    Otherwise, creates placeholder credentials for public APIs.

    Args:
        gateway_id: ID of the gateway
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

    # Create gateway target
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


@app.get("/", response_model=HealthCheckResponse)
async def health_check():
    """Health check endpoint"""
    return HealthCheckResponse(
        status="healthy",
        message="AgentCore Gateway Tools API is running"
    )


@app.post("/gateways", response_model=CreateGatewayResponse)
async def create_gateway_endpoint(request: CreateGatewayRequest):
    """Create a new gateway with provided authentication configuration"""
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

        # Create or get gateway with JWT auth
        auth_config = {
            "client_id": request.auth_config.client_id,
            "discovery_url": request.auth_config.discovery_url,
        }
        
        gateway_info = create_gateway(
            gateway_name=request.gateway_name,
            role_arn=role_arn,
            is_authenticated=True,
            auth_config=auth_config,
            description=request.description
        )

        return CreateGatewayResponse(
            status="success",
            gateway_id=gateway_info["gateway_id"],
            gateway_url=gateway_info["gateway_url"],
            gateway_name=gateway_info["gateway_name"],
            message=f"Gateway '{request.gateway_name}' successfully created"
        )

    except HTTPException:
        raise
    except Exception as e:
        print(f"Error creating gateway: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create gateway: {str(e)}"
        )


@app.post("/gateways/no-auth", response_model=CreateGatewayResponse)
async def create_gateway_no_auth_endpoint(request: CreateGatewayNoAuthRequest):
    """Create a new gateway without authentication"""
    try:
        # Create IAM role
        role_arn = create_agentcore_gateway_role("sample-lambdagateway-role-demo")

        # Create or get gateway without auth
        gateway_info = create_gateway(
            gateway_name=request.gateway_name,
            role_arn=role_arn,
            is_authenticated=False,
            description=request.description
        )

        return CreateGatewayResponse(
            status="success",
            gateway_id=gateway_info["gateway_id"],
            gateway_url=gateway_info["gateway_url"],
            gateway_name=gateway_info["gateway_name"],
            message=f"Gateway '{request.gateway_name}' successfully created without authentication"
        )

    except HTTPException:
        raise
    except Exception as e:
        print(f"Error creating gateway (no auth): {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create gateway: {str(e)}"
        )


# Creates tool from uploaded OpenAPI spec file
@app.post("/tools", response_model=CreateToolResponse)
async def create_tool(
    gateway_id: str = Form(...),
    tool_name: str = Form(...),
    openapi_spec_file: UploadFile = File(...),
    auth: str = Form(...),  # JSON string of Auth object
):
    """Create a new tool on the gateway"""
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

        # Register tool with gateway
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
            message=f"Tool '{tool_name}' successfully created and registered on gateway {gateway_id}",
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
    """Create a new tool on the gateway from an OpenAPI spec URL"""
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

        # Upload to S3 and register tool with gateway
        s3_uri = upload_openapi_spec(spec_json, request.tool_name, request.gateway_id, bucket_name=OPENAPI_SPECS_BUCKET)

        # Register tool with gateway
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
            message=f"Tool '{request.tool_name}' successfully created and registered on gateway {request.gateway_id}",
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
    """Create a new tool on the gateway from manual API information"""
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

        # Register tool with gateway
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
            message=f"Tool '{request.tool_name}' successfully created and registered on gateway {request.gateway_id}",
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
    """Create a new tool on the gateway from an inline OpenAPI spec definition"""
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

        # Register tool with gateway
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
            message=f"Tool '{request.tool_name}' successfully created and registered on gateway {request.gateway_id}",
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


# TODO: Add a method to update a tool or target on the gateway

# Deletes target from gateway - A target can be 1 tool or multiple tools
@app.delete("/gateways/{gateway_id}/tools/{target_id}", response_model=DeleteToolResponse)
async def delete_tool(gateway_id: str, target_id: str):
    """
    Delete a tool (target) from a gateway.

    Args:
        gateway_id: The unique identifier of the gateway
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
            message=f"Tool '{target_id}' deletion initiated on gateway '{gateway_id}'"
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


# Health check for tools management
@app.get("/health")
async def health():
    """Check if tools management is available"""
    return {
        "status": "ready",
        "openapi_specs_bucket": OPENAPI_SPECS_BUCKET,
        "aws_region": AWS_REGION
    }


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
