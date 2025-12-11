# Gateway Tools API

REST API for creating and managing OpenAPI tools on AgentCore Gateway.

## Quick Start

```bash
# Start the server
python -m uvicorn api.main:app --reload

# Or
python api/main.py
```

Visit `http://localhost:8000/docs` for interactive API documentation.

## Endpoints

### Health Check
- `GET /` - Check if API is running
- `GET /tools/health` - Check tool service status

### Create Gateway
- `POST /gateways` - Create a new gateway

**Parameters (JSON):**
- `gateway_name` (required) - Name for the gateway
- `description` (optional) - Gateway description

**Response (success):**
```json
{
  "status": "success",
  "gateway_id": "gw-xyz",
  "gateway_url": "https://...",
  "gateway_name": "MyGateway",
  "message": "Gateway 'MyGateway' successfully created"
}
```

### Create Tool
- `POST /tools` - Create a new tool

**Parameters (form data):**
- `gateway_id` (required) - Target gateway ID
- `tool_name` (required) - Name for the tool
- `openapi_spec_file` (required) - OpenAPI JSON file
- `auth` (required) - JSON object with authentication config

**Auth Object Schema:**
```json
{
  "type": "api_key" | "oauth",
  "provider_name": "string (required for api_key auth)",
  "config": {
    "api_key": "string (required for api_key auth)",
    "api_key_param_name": "string (default: 'api_key')",
    "api_key_location": "QUERY_PARAMETER" | "HEADER" (default: "QUERY_PARAMETER")
  }
}
```

**Response (success):**
```json
{
  "status": "success",
  "tool_name": "MyTool",
  "gateway_id": "gw-xyz",
  "openapi_spec_path": "/path/to/spec.json",
  "message": "Tool 'MyTool' successfully created..."
}
```

## Example

### cURL
```bash
curl -X POST http://localhost:8000/tools \
  -F "gateway_id=gw-abc123" \
  -F "tool_name=MyTool" \
  -F "openapi_spec_file=@spec.json" \
  -F 'auth={"type":"api_key","provider_name":"MyProvider","config":{"api_key":"your-key"}}'
```

### Python
```python
import requests
import json

with open("spec.json", "rb") as f:
    response = requests.post(
        "http://localhost:8000/tools",
        files={"openapi_spec_file": f},
        data={
            "gateway_id": "gw-abc123",
            "tool_name": "MyTool",
            "auth": json.dumps({
                "type": "api_key",
                "provider_name": "MyProvider",
                "config": {
                    "api_key": "your-key",
                    "api_key_param_name": "api_key",
                    "api_key_location": "QUERY_PARAMETER"
                }
            })
        }
    )
    print(response.json())
```

## Workflow

1. Validates input parameters and OpenAPI spec
2. Saves spec to `openapi_specs/` directory
3. Calls `tools.add_tool_to_gateway()` which:
   - Uploads spec to S3
   - Creates credential provider (if API key auth)
   - Registers tool as gateway target
4. Returns success response

## Error Handling

| Error | Solution |
|-------|----------|
| `api_key is required in auth.config` | Provide api_key in auth.config when type is `api_key` |
| `auth.provider_name is required` | Provide provider_name for API key auth |
| `Invalid JSON` | Validate OpenAPI spec JSON format |
| `OpenAPI spec must contain 'openapi' or 'swagger' field` | Ensure spec has proper structure |

## Files

- `main.py` - FastAPI application and endpoints
- `types.py` - Request/response type definitions (Auth, AuthConfig, etc.)
- `__init__.py` - Package initialization
- `README.md` - This file

## Environment

- `AWS_DEFAULT_REGION` - AWS region (default: us-east-1)
- AWS credentials required (via environment or IAM role)

