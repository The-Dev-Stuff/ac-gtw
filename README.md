# AgentCore Gateway MCP Server

Transform OpenAPI specs into MCP tools via AWS Bedrock AgentCore Gateway.

This repository automates the creation of a modular gateway infrastructure with reusable authentication, gateway deployment, and tool management components.

## Quick Start

```bash
# Setup
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# Configure
export AWS_DEFAULT_REGION=us-east-1
export NASA_API_KEY=your_nasa_key_here

# Run
python main.py
```

## API Server (FastAPI)

Alternatively, use the REST API to create tools via HTTP requests:

```bash
# Start the API server
python -m uvicorn api.main:app --reload
# API available at http://localhost:8000
# Interactive docs at http://localhost:8000/docs
```

See [api/README.md](api/README.md) for API documentation and examples.

## Architecture Overview

The project is organized into **three modular, reusable components** in separate folders:

```
auth/
  ├── __init__.py
  └── cognito_setup.py    → Create Cognito auth (ONE-TIME, reusable)

gateway/
  ├── __init__.py
  └── manage_gateway.py   → Create/manage MCP gateway (REUSABLE for multiple gateways)

tools/
  ├── __init__.py
  └── manage_tools.py     → Add OpenAPI tools (REUSABLE for multiple tools)
```

### Module Details

#### 1. **auth/** - Authentication Setup (Run Once)
Creates JWT authentication infrastructure for the gateway.

**Module:** `auth/cognito_setup.py`

**Creates:**
- Cognito user pool, resource server, and M2M client
- OpenID discovery URL

**Returns:** Authentication config (reusable across all gateways)

**Usage:**
```python
from auth import setup_auth
auth_config = setup_auth()  # Save this for future use
```

#### 2. **gateway/** - Gateway Management (Reusable)
Creates or retrieves an MCP gateway with JWT authorization and manages the IAM role.

**Module:** `gateway/manage_gateway.py`

**Functions:**
- `setup_gateway(gateway_name, auth_config)` - Create/retrieve gateway (also creates IAM role)
- `create_or_get_gateway()` - Low-level gateway creation
- `create_agentcore_gateway_role()` - Create IAM role for gateway
- `delete_gateway()` - Delete a gateway

**Returns:** Gateway ID, URL, and name

**Usage:**
```python
from gateway import setup_gateway
gw = setup_gateway("MyGateway", auth_config)
print(f"Gateway URL: {gw['gateway_url']}")
```

#### 3. **tools/** - Tool Management (Reusable)
Adds OpenAPI tools to a gateway with credential injection.

**Module:** `tools/manage_tools.py`

**Functions:**
- `add_tool_to_gateway(gateway_id, ...)` - Add a tool
- `create_gateway_target()` - Low-level target creation
- `upload_openapi_to_s3()` - Upload OpenAPI spec
- `create_or_get_api_key_credential_provider()` - Create credential provider

**Handles:**
- Uploading OpenAPI specs to S3
- Creating credential providers for external APIs
- Configuring credential injection (query params, headers)

**Usage:**
```python
from tools import add_tool_to_gateway

response = add_tool_to_gateway(
    gateway_id="gw-xyz",
    target_name="NasaMarsInsights",
    openapi_file_path="openapi_specs/nasa_mars_insights_openapi.json",
    api_key="your-api-key",
    api_key_provider_name="NasaAPIKey",
    api_key_param_name="api_key",
    api_key_location="QUERY_PARAMETER"
)
```

### main.py
Orchestrates all three steps for a complete fresh setup. Import individual modules for selective operations.

## Usage Patterns

### Pattern 1: Fresh Setup (All Steps)
```bash
python main.py
```

### Pattern 2: Reuse Auth, New Gateway
```python
from gateway import setup_gateway
from tools import add_tool_to_gateway

auth_config = {...}  # From previous setup_auth() call
gw = setup_gateway("GatewayB", auth_config)
add_tool_to_gateway(gw["gateway_id"], "Tool1", "spec.json", ...)
```

### Pattern 3: Existing Gateway, Add Tool
```python
from tools import add_tool_to_gateway

add_tool_to_gateway(
    gateway_id="gw-existing-id",
    target_name="Tool2",
    openapi_file_path="spec.json",
    api_key="key",
    api_key_provider_name="MyAPIKey"
)
```

### Pattern 4: Existing Gateway, Add Multiple Tools
```python
from tools import add_tool_to_gateway

# Same gateways, different tools
add_tool_to_gateway(gw_id, "Tool1", "spec1.json", ...)
add_tool_to_gateway(gw_id, "Tool2", "spec2.json", ...)
add_tool_to_gateway(gw_id, "Tool3", "spec3.json", ...)
```

## Configuration

### Environment Variables
- `AWS_DEFAULT_REGION` - AWS region (default: us-east-1)
- `NASA_API_KEY` - NASA API key

### Hard-coded Defaults (in each module)
Modify the CONFIG sections in each script:
- **auth/cognito_setup.py:** Cognito pool name, client name
- **gateway/manage_gateway.py:** Gateway name, IAM role name
- **tools/manage_tools.py:** No hard-coded config; all parameters are function arguments

## AWS Resources Created

```
IAM Role
Cognito User Pool + Resource Server + M2M Client
Bedrock AgentCore Gateway
Bedrock AgentCore Credential Providers (for API keys)
S3 Bucket (for OpenAPI specs)
```

## Testing

After running `main.py`:

1. **Get Cognito Token:**
```python
from auth import get_token

token_response = get_token(
    user_pool_id=auth_config["user_pool_id"],
    client_id=auth_config["client_id"],
    client_secret=auth_config["client_secret"],
    scope=f"{auth_config['resource_server_id']}/gateways:read",
    region="us-east-1"
)
```

2. **Call Gateway:**
Use the `gatewayUrl` and token with an MCP client to list tools and invoke them.

## Error Handling

| Scenario | Behavior |
|----------|----------|
| Auth already exists | Reuses existing resources |
| Gateway name exists | Retrieves existing gateway |
| Tool name exists | Raises error (use unique name or delete first) |
| Missing auth config | Raises clear error message |

## Documentation

- **ARCHITECTURE.md** - Detailed architecture and design patterns
- **QUICKREF.md** - Quick reference for functions and return values
- **DIAGRAMS.md** - Visual diagrams and data flow

## Cleanup

This creates AWS resources (IAM, Cognito, S3, Gateway targets). Delete them when finished:

```python
from gateway import delete_gateway
from tools import delete_gateway_target

# Delete tools first
delete_gateway_target(gateway_id, target_name)

# Then delete gateways
delete_gateway(gateway_id)
```

Note: Cognito resources can be reused across gateways, so they're often left in place.
