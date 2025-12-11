"""
auth module
Handles Cognito authentication setup for AgentCore Gateway.
"""
from .cognito_setup import (
    setup_auth,
    get_token,
    get_or_create_user_pool,
    get_or_create_resource_server,
    get_or_create_m2m_client
)

__all__ = [
    "setup_auth",
    "get_token",
    "get_or_create_user_pool",
    "get_or_create_resource_server",
    "get_or_create_m2m_client"
]

