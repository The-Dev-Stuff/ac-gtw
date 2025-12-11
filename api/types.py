"""
types.py
Request/Response models and type definitions for the API
"""
from typing import Literal, Optional
from pydantic import BaseModel


class AuthConfig(BaseModel):
    """Authentication configuration for external API"""
    api_key: Optional[str] = None
    api_key_param_name: str = "api_key"
    api_key_location: Literal["QUERY_PARAMETER", "HEADER"] = "QUERY_PARAMETER"


class Auth(BaseModel):
    """Authentication object"""
    type: Literal["oauth", "api_key"]
    provider_name: Optional[str] = None
    config: AuthConfig


class CognitoAuthConfig(BaseModel):
    """Cognito authentication configuration for gateway"""
    user_pool_id: str
    client_id: str
    discovery_url: str


class HealthCheckResponse(BaseModel):
    """Health check response"""
    status: str
    message: str


class CreateToolResponse(BaseModel):
    """Response after creating a tool"""
    status: str
    tool_name: str
    gateway_id: str
    openapi_spec_path: str
    message: str

class CreateToolFromUrlRequest(BaseModel):
    """Request to create a tool from a URL to an OpenAPI spec"""
    gateway_id: str
    tool_name: str
    openapi_spec_url: str
    auth: Auth

class CreateGatewayRequest(BaseModel):
    """Request to create a gateway"""
    gateway_name: str
    description: Optional[str] = None
    auth_config: CognitoAuthConfig


class CreateGatewayResponse(BaseModel):
    """Response after creating a gateway"""
    status: str
    gateway_id: str
    gateway_url: str
    gateway_name: str
    message: str


