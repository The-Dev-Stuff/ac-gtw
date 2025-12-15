"""
models.py
Request/Response models and type definitions for the API
"""
from datetime import datetime
from typing import Any, Literal, Optional
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
    """Cognito authentication configuration for gateways"""
    user_pool_id: str
    client_id: str
    discovery_url: str


class HealthCheckResponse(BaseModel):
    """Health check response"""
    status: str
    message: str
    openapi_specs_bucket: Optional[str] = None
    aws_region: Optional[str] = None


class CreateToolResponse(BaseModel):
    """Response after creating a tool - includes all fields from AWS SDK response"""
    status: str
    tool_name: str
    gateway_id: str
    openapi_spec_path: str
    message: str
    # AWS SDK response fields
    target_id: Optional[str] = None
    gateway_arn: Optional[str] = None
    description: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    last_synchronized_at: Optional[datetime] = None
    target_status: Optional[str] = None
    status_reasons: Optional[list[str]] = None
    target_configuration: Optional[dict[str, Any]] = None
    credential_provider_configurations: Optional[list[dict[str, Any]]] = None


class CreateToolFromUrlRequest(BaseModel):
    """Request to create a tool from a URL to an OpenAPI spec"""
    gateway_id: str
    tool_name: str
    openapi_spec_url: str
    auth: Auth


class ApiInfo(BaseModel):
    """API information for manual tool creation"""
    method: str
    url: str
    query_params: Optional[dict] = None
    headers: Optional[dict] = None
    body_schema: Optional[dict] = None
    description: Optional[str] = None


class CreateToolFromApiInfoRequest(BaseModel):
    """Request to create a tool from manual API information"""
    gateway_id: str
    tool_name: str
    api_info: ApiInfo
    auth: Optional[Auth] = None


class CreateToolFromSpecRequest(BaseModel):
    """Request to create a tool from an inline OpenAPI spec"""
    gateway_id: str
    tool_name: str
    openapi_spec: dict
    auth: Optional[Auth] = None


class CreateGatewayRequest(BaseModel):
    """Request to create a gateways"""
    gateway_name: str
    description: Optional[str] = None
    auth_config: CognitoAuthConfig


class CreateGatewayNoAuthRequest(BaseModel):
    """Request to create a gateways without authentication"""
    gateway_name: str
    description: Optional[str] = None


class CreateGatewayResponse(BaseModel):
    """Response after creating a gateway - includes all fields from AWS SDK response"""
    status: str
    message: str
    # AWS SDK response fields
    gateway_id: Optional[str] = None
    gateway_url: Optional[str] = None
    gateway_arn: Optional[str] = None
    name: Optional[str] = None
    description: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    gateway_status: Optional[str] = None
    status_reasons: Optional[list[str]] = None
    authorizer_type: Optional[str] = None
    protocol_type: Optional[str] = None
    role_arn: Optional[str] = None
    authorizer_configuration: Optional[dict[str, Any]] = None
    protocol_configuration: Optional[dict[str, Any]] = None
    exception_level: Optional[str] = None
    interceptor_configurations: Optional[list[dict[str, Any]]] = None
    policy_engine_configuration: Optional[dict[str, Any]] = None
    kms_key_arn: Optional[str] = None
    workload_identity_details: Optional[dict[str, Any]] = None


class UpdateGatewayRequest(BaseModel):
    """Request payload to update a gateway"""
    name: str
    protocol_type: str
    authorizer_type: str
    role_arn: str
    description: Optional[str] = None


class UpdateGatewayResponse(BaseModel):
    """Response after updating a gateway - includes all fields from AWS SDK response"""
    status: str
    message: str
    # AWS SDK response fields
    gateway_id: Optional[str] = None
    gateway_url: Optional[str] = None
    gateway_arn: Optional[str] = None
    name: Optional[str] = None
    description: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    gateway_status: Optional[str] = None
    status_reasons: Optional[list[str]] = None
    authorizer_type: Optional[str] = None
    protocol_type: Optional[str] = None
    role_arn: Optional[str] = None
    authorizer_configuration: Optional[dict[str, Any]] = None
    protocol_configuration: Optional[dict[str, Any]] = None
    exception_level: Optional[str] = None
    interceptor_configurations: Optional[list[dict[str, Any]]] = None
    policy_engine_configuration: Optional[dict[str, Any]] = None
    kms_key_arn: Optional[str] = None
    workload_identity_details: Optional[dict[str, Any]] = None


class GetGatewayResponse(BaseModel):
    """Response after retrieving a gateway - includes all fields from AWS SDK response"""
    status: str
    message: str
    # AWS SDK response fields
    gateway_id: Optional[str] = None
    gateway_url: Optional[str] = None
    gateway_arn: Optional[str] = None
    name: Optional[str] = None
    description: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    gateway_status: Optional[str] = None
    status_reasons: Optional[list[str]] = None
    authorizer_type: Optional[str] = None
    protocol_type: Optional[str] = None
    role_arn: Optional[str] = None
    authorizer_configuration: Optional[dict[str, Any]] = None
    protocol_configuration: Optional[dict[str, Any]] = None
    exception_level: Optional[str] = None
    interceptor_configurations: Optional[list[dict[str, Any]]] = None
    policy_engine_configuration: Optional[dict[str, Any]] = None
    kms_key_arn: Optional[str] = None
    workload_identity_details: Optional[dict[str, Any]] = None


class GatewaySummary(BaseModel):
    """Summary of a gateway in the list"""
    gateway_id: Optional[str] = None
    name: Optional[str] = None
    description: Optional[str] = None
    gateway_status: Optional[str] = None
    authorizer_type: Optional[str] = None
    protocol_type: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class UpdateToolRequest(BaseModel):
    """Request body for updating a tool"""
    target_name: str
    target_configuration: Optional[dict[str, Any]] = None
    credential_provider_configurations: Optional[list[dict[str, Any]]] = None
    description: Optional[str] = None


class ListGatewaysResponse(BaseModel):
    """Response after listing gateways"""
    status: str
    message: str
    items: list[GatewaySummary]
    next_token: Optional[str] = None


class UpdateToolResponse(BaseModel):
    """Response after updating a tool - includes all fields from AWS SDK response"""
    status: str
    tool_name: str
    target_id: str
    gateway_id: str
    message: str
    # AWS SDK response fields
    gateway_arn: Optional[str] = None
    description: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    last_synchronized_at: Optional[datetime] = None
    target_status: Optional[str] = None
    status_reasons: Optional[list[str]] = None
    target_configuration: Optional[dict[str, Any]] = None
    credential_provider_configurations: Optional[list[dict[str, Any]]] = None


class GetGatewayTargetResponse(BaseModel):
    """Response after retrieving a gateway target - includes all fields from AWS SDK response"""
    status: str
    message: str
    # AWS SDK response fields
    target_id: Optional[str] = None
    name: Optional[str] = None
    description: Optional[str] = None
    gateway_arn: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    last_synchronized_at: Optional[datetime] = None
    target_status: Optional[str] = None
    status_reasons: Optional[list[str]] = None
    target_configuration: Optional[dict[str, Any]] = None
    credential_provider_configurations: Optional[list[dict[str, Any]]] = None


class TargetSummary(BaseModel):
    """Summary of a gateway target in the list"""
    target_id: Optional[str] = None
    name: Optional[str] = None
    description: Optional[str] = None
    target_status: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class ListGatewayTargetsResponse(BaseModel):
    """Response after listing gateway targets"""
    status: str
    message: str
    items: list[TargetSummary]
    next_token: Optional[str] = None


class DeleteToolResponse(BaseModel):
    """Response after deleting a tool"""
    status: str
    target_id: str
    gateway_id: str
    gateway_arn: Optional[str] = None
    status_reasons: Optional[list[str]] = None
    message: str


class DeleteGatewayResponse(BaseModel):
    """Response after deleting a gateway"""
    gateway_id: str
    status: str
    status_reasons: Optional[list[str]] = None

