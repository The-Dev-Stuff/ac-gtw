"""
openapi_generator.py
Generates OpenAPI 3.0 spec from minimal API information.
"""
from typing import Optional
from urllib.parse import urlparse


def _to_camel_case(s: str) -> str:
    """Convert string to camelCase."""
    parts = s.replace("-", "_").split("_")
    return parts[0].lower() + "".join(word.capitalize() for word in parts[1:])


def _extract_path_from_url(url: str) -> tuple[str, str]:
    """
    Extract base URL and path from full URL.

    Returns:
        Tuple of (base_url, path)
    """
    parsed = urlparse(url)
    base_url = f"{parsed.scheme}://{parsed.netloc}"
    path = parsed.path or "/"
    return base_url, path


def _json_schema_to_parameters(schema: dict, location: str) -> list[dict]:
    """
    Convert JSON Schema object to OpenAPI parameters list.

    Args:
        schema: JSON Schema with properties
        location: 'query' or 'header'

    Returns:
        List of OpenAPI parameter objects
    """
    parameters = []
    properties = schema.get("properties", {})
    required_fields = schema.get("required", [])

    for name, prop in properties.items():
        param = {
            "name": name,
            "in": location,
            "required": name in required_fields,
            "schema": {
                "type": prop.get("type", "string")
            }
        }
        if "description" in prop:
            param["description"] = prop["description"]
        if "enum" in prop:
            param["schema"]["enum"] = prop["enum"]

        parameters.append(param)

    return parameters


def generate_openapi_spec(
    tool_name: str,
    method: str,
    url: str,
    query_params: Optional[dict] = None,
    headers: Optional[dict] = None,
    body_schema: Optional[dict] = None,
    description: Optional[str] = None
) -> dict:
    """
    Generate an OpenAPI 3.0 spec from minimal API information.

    Args:
        tool_name: Name of the tool (used for title and operation ID)
        method: HTTP method (GET, POST, PUT, DELETE, etc.)
        url: Full URL including path
        query_params: JSON Schema object for query parameters
        headers: JSON Schema object for headers
        body_schema: JSON Schema object for request body
        description: Optional description for the operation

    Returns:
        Valid OpenAPI 3.0 spec as dict
    """
    base_url, path = _extract_path_from_url(url)
    method_lower = method.lower()

    # Generate operation ID: {tool_name}__{pathCamelCase}
    path_part = path.strip("/").replace("/", "_")
    operation_id = f"{tool_name}__{_to_camel_case(path_part)}" if path_part else f"{tool_name}__root"

    # Build parameters list
    parameters = []
    if query_params:
        parameters.extend(_json_schema_to_parameters(query_params, "query"))
    if headers:
        parameters.extend(_json_schema_to_parameters(headers, "header"))

    # Build operation object
    operation = {
        "summary": description or f"{method.upper()} {path}",
        "operationId": operation_id,
        "responses": {
            "200": {
                "description": "Successful response",
                "content": {
                    "application/json": {
                        "schema": {
                            "type": "object"
                        }
                    }
                }
            }
        }
    }

    if parameters:
        operation["parameters"] = parameters

    if description:
        operation["description"] = description

    # Add request body for methods that support it
    if body_schema and method_lower in ("post", "put", "patch"):
        operation["requestBody"] = {
            "required": True,
            "content": {
                "application/json": {
                    "schema": body_schema
                }
            }
        }

    # Build full OpenAPI spec
    spec = {
        "openapi": "3.0.3",
        "info": {
            "title": tool_name,
            "description": description or f"API spec for {tool_name}",
            "version": "1.0.0"
        },
        "servers": [
            {
                "url": base_url
            }
        ],
        "paths": {
            path: {
                method_lower: operation
            }
        }
    }

    return spec

