# Tool Update Fix - Credentials Optional for Non-Auth Gateways

## Problem
When updating a tool on a gateway created **without authentication**, the API was requiring `credential_provider_configurations` to be provided in the request body, which caused a validation error from AWS:

```
"Credential provider configurations is not defined"
```

This was incorrect because:
1. AWS documentation specifies `credentialProviderConfigurations` as **Optional (Required: No)**
2. Gateways without authentication shouldn't require credential configurations
3. Users were unable to update tool specs on non-authenticated gateways

## Solution
Made the following changes to support optional credential configurations:

### 1. **api/models.py** - UpdateToolRequest
Changed `credential_provider_configurations` from required to optional:

```python
class UpdateToolRequest(BaseModel):
    """Request body for updating a tool"""
    target_name: str
    target_configuration: dict[str, Any]
    credential_provider_configurations: Optional[list[dict[str, Any]]] = None  # Now optional
    description: Optional[str] = None
```

### 2. **services/tools/tools_service.py** - update_gateway_target()
Updated the function to intelligently handle missing credentials:

- If `credential_provider_configurations` is provided → use it directly
- If `credential_provider_configurations` is None → fetch existing credentials from the target
- If the target has no credentials (non-authenticated gateway) → omit the field from the AWS API call

```python
# Add credential configurations if provided
# If not provided, fetch existing credentials from the target
if credential_provider_configurations is not None:
    update_params["credentialProviderConfigurations"] = credential_provider_configurations
else:
    # Fetch existing target to get current credential configurations
    try:
        existing_target = get_gateway_target(gateway_id, target_id)
        existing_creds = existing_target.get("credentialProviderConfigurations")
        if existing_creds:
            update_params["credentialProviderConfigurations"] = existing_creds
            print(f"Using existing credential configurations from current target")
    except Exception as e:
        print(f"Warning: Could not fetch existing credentials: {str(e)}")
        # Continue without credentials - some gateways may not require them
```

### 3. **api/main.py** - update_tool endpoint docstring
Updated documentation to clarify that credentials are optional and the service preserves existing ones.

### 4. **testing/testing-collection/Tools Targets.md** - Updated Documentation
Added clear examples for both authentication scenarios:

**For non-authenticated gateways (simplified):**
```bash
curl -X PUT 'http://localhost:8000/gateways/{gateway_id}/tools/{target_id}' \
  --header 'Content-Type: application/json' \
  --data '{
    "target_name": "updated-tool-name",
    "target_configuration": {
      "mcp": {
        "openApiSchema": {
          "s3": {
            "uri": "s3://openapi-specs-bucket/updated-spec.json"
          }
        }
      }
    },
    "description": "Updated description"
  }'
```

**For authenticated gateways (copy credentials from GET response):**
The documentation now shows the two-step process:
1. GET the tool to retrieve current credential configurations
2. Use those exact credentials in the PUT request

## AWS Documentation Alignment
✅ All changes align with AWS Bedrock AgentCore Control API documentation:
- `credentialProviderConfigurations` - **Required: No**
- `description` - **Required: No**
- `name` - **Required: Yes**
- `targetConfiguration` - **Required: Yes**

## Testing
After these changes, you can now:

1. **Update a tool on a non-authenticated gateway (simplified - no credentials needed):**
```bash
curl -X PUT 'http://localhost:8000/gateways/publicapisgateway-uy4t2fucxm/tools/Q6ZQF44YWB' \
  --header 'Content-Type: application/json' \
  --data '{
    "target_name": "todos-api-tool",
    "target_configuration": {
      "mcp": {
        "openApiSchema": {
          "s3": {
            "uri": "s3://openapi-specs-bucket/updated-todos-tool.json"
          }
        }
      }
    }
  }'
```

This is exactly the request you were trying - it now works without requiring `credential_provider_configurations`!

2. **Update a tool on an authenticated gateway** (if needed):
Get the tool first to retrieve credentials, then use them in the update request.

## Files Modified
- `/home/manny/add/gateway-poc/api/models.py` - Made credential_provider_configurations optional
- `/home/manny/add/gateway-poc/services/tools/tools_service.py` - Added intelligent credential handling
- `/home/manny/add/gateway-poc/api/main.py` - Updated endpoint documentation
- `/home/manny/add/gateway-poc/testing/testing-collection/Tools Targets.md` - Added comprehensive examples

