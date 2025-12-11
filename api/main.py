"""
main.py
FastAPI application for managing gateway tools.
"""
import os
import json
from pathlib import Path
import requests

from fastapi import FastAPI, UploadFile, File, Form, HTTPException, status

from gateway import setup_gateway
from tools import add_tool_to_gateway
from .types import HealthCheckResponse, CreateToolResponse, CreateGatewayRequest, CreateGatewayResponse, Auth, CreateToolFromUrlRequest

# CONFIG
AWS_REGION = os.environ.get("AWS_DEFAULT_REGION", "us-east-1")
OPENAPI_SPECS_DIR = Path("openapi_specs")

# Ensure openapi_specs directory exists
OPENAPI_SPECS_DIR.mkdir(exist_ok=True)

# Create FastAPI app
app = FastAPI(
    title="AgentCore Gateway Tools API",
    description="API for managing OpenAPI tools on AgentCore Gateway",
    version="1.0.0"
)


@app.get("/", response_model=HealthCheckResponse)
async def health_check():
    """Health check endpoint"""
    return HealthCheckResponse(
        status="healthy",
        message="AgentCore Gateway Tools API is running"
    )


@app.post("/gateways", response_model=CreateGatewayResponse)
async def create_gateway(request: CreateGatewayRequest):
    """Create a new gateway with provided authentication configuration"""
    try:
        # Build auth config from request
        auth_config = {
            "user_pool_id": request.auth_config.user_pool_id,
            "client_id": request.auth_config.client_id,
            "discovery_url": request.auth_config.discovery_url,
        }

        # Setup gateway with provided auth config
        gateway_info = setup_gateway(
            gateway_name=request.gateway_name,
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
        if auth_obj.type == "api_key":
            if not auth_obj.config.api_key:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="api_key is required in auth.config when auth.type is 'api_key'"
                )
            if not auth_obj.provider_name:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="auth.provider_name is required when auth.type is 'api_key'"
                )

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

        # Save OpenAPI spec to local directory
        spec_filename = f"{tool_name}_openapi.json"
        spec_filepath = OPENAPI_SPECS_DIR / spec_filename

        with open(spec_filepath, "w") as f:
            json.dump(spec_json, f, indent=2)

        print(f"✓ OpenAPI spec saved to {spec_filepath}")

        # Call the manage_tools function to add tool to gateway
        add_tool_to_gateway(
            gateway_id=gateway_id,
            target_name=tool_name,
            openapi_file_path=str(spec_filepath),
            api_key=auth_obj.config.api_key if auth_obj.type == "api_key" else None,
            api_key_provider_name=auth_obj.provider_name if auth_obj.type == "api_key" else None,
            api_key_param_name=auth_obj.config.api_key_param_name,
            api_key_location=auth_obj.config.api_key_location,
            description=None
        )

        return CreateToolResponse(
            status="success",
            tool_name=tool_name,
            gateway_id=gateway_id,
            openapi_spec_path=str(spec_filepath),
            message=f"Tool '{tool_name}' successfully created and registered on gateway {gateway_id}"
        )

    except HTTPException:
        raise
    except Exception as e:
        print(f"Error creating tool: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create tool: {str(e)}"
        )


@app.post("/tools/from-url", response_model=CreateToolResponse)
async def create_tool_from_url(request: CreateToolFromUrlRequest):
    """Create a new tool on the gateway from an OpenAPI spec URL"""
    try:
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

        # Save to local directory
        spec_filename = f"{request.tool_name}_openapi.json"
        spec_filepath = OPENAPI_SPECS_DIR / spec_filename

        with open(spec_filepath, "w") as f:
            json.dump(spec_json, f, indent=2)

        print(f"✓ OpenAPI spec saved to {spec_filepath}")

        # Add tool to gateway
        add_tool_to_gateway(
            gateway_id=request.gateway_id,
            target_name=request.tool_name,
            openapi_file_path=str(spec_filepath),
            api_key=request.auth.config.api_key if request.auth.type == "api_key" else None,
            api_key_provider_name=request.auth.provider_name if request.auth.type == "api_key" else None,
            api_key_param_name=request.auth.config.api_key_param_name,
            api_key_location=request.auth.config.api_key_location,
            description=None
        )

        return CreateToolResponse(
            status="success",
            tool_name=request.tool_name,
            gateway_id=request.gateway_id,
            openapi_spec_path=str(spec_filepath),
            message=f"Tool '{request.tool_name}' successfully created and registered on gateway {request.gateway_id}"
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


@app.get("/tools/health")
async def tools_health():
    """Check if tools management is available"""
    return {
        "status": "ready",
        "openapi_specs_dir": str(OPENAPI_SPECS_DIR.absolute()),
        "aws_region": AWS_REGION
    }


if __name__ == "__main__":
    import uvicorn

    print("Starting AgentCore Gateway Tools API...")
    print(f"OpenAPI specs directory: {OPENAPI_SPECS_DIR.absolute()}")
    print(f"AWS Region: {AWS_REGION}")

    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8000,
        log_level="info"
    )

