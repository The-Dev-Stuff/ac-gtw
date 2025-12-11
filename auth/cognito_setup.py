"""
cognito_setup.py
One-time setup of Cognito authentication infrastructure for AgentCore Gateway.
This creates the user pool, resource server, and M2M client.
These resources can be reused across multiple gateways.
"""
import os
import json
import boto3
from botocore.exceptions import ClientError

# CONFIG: change these as needed
AWS_REGION = os.environ.get("AWS_DEFAULT_REGION", "us-east-1")
COGNITO_USER_POOL_NAME = "sample-agentcore-gateway-pool"
RESOURCE_SERVER_ID = "sample-agentcore-gateway-id"
RESOURCE_SERVER_NAME = "sample-agentcore-gateway-name"
CLIENT_NAME = "sample-agentcore-gateway-client"


def get_or_create_user_pool(cognito_client, pool_name):
    """
    Gets or creates a Cognito user pool.
    """
    # try to find existing
    pools = cognito_client.list_user_pools(MaxResults=60).get("UserPools", [])
    for p in pools:
        if p["Name"] == pool_name:
            return p["Id"]

    resp = cognito_client.create_user_pool(PoolName=pool_name)
    return resp["UserPool"]["Id"]


def get_or_create_resource_server(cognito_client, user_pool_id, identifier, name, scopes):
    """
    Gets or creates a Cognito resource server.
    """
    # list existing servers
    try:
        existing = cognito_client.list_resource_servers(UserPoolId=user_pool_id).get("ResourceServers", [])
        for rs in existing:
            if rs["Identifier"] == identifier:
                return rs
    except Exception:
        pass

    resp = cognito_client.create_resource_server(
        UserPoolId=user_pool_id,
        Identifier=identifier,
        Name=name,
        Scopes=scopes
    )
    return resp


def get_or_create_m2m_client(cognito_client, user_pool_id, client_name, resource_server_id):
    """
    Creates or returns an existing confidential client configured for client credentials.
    """
    clients = cognito_client.list_user_pool_clients(UserPoolId=user_pool_id, MaxResults=60).get("UserPoolClients", [])
    for c in clients:
        if c["ClientName"] == client_name:
            client_id = c["ClientId"]
            # retrieving secret requires describe
            desc = cognito_client.describe_user_pool_client(UserPoolId=user_pool_id, ClientId=client_id)
            return client_id, desc["UserPoolClient"].get("ClientSecret")

    resp = cognito_client.create_user_pool_client(
        UserPoolId=user_pool_id,
        ClientName=client_name,
        GenerateSecret=True,
        AllowedOAuthFlows=["client_credentials"],
        AllowedOAuthScopes=[f"{resource_server_id}/gateway:read", f"{resource_server_id}/gateway:write"],
        AllowedOAuthFlowsUserPoolClient=True
    )
    client_id = resp["UserPoolClient"]["ClientId"]
    client_secret = resp["UserPoolClient"].get("ClientSecret")
    return client_id, client_secret


def get_token(user_pool_id, client_id, client_secret, scope, region):
    """
    Performs client_credentials flow against Cognito token endpoint.
    scope: space-separated string of scopes
    Returns token json.
    """
    import requests
    discovery = f"https://cognito-idp.{region}.amazonaws.com/{user_pool_id}/.well-known/openid-configuration"
    disc = requests.get(discovery).json()
    token_url = disc["token_endpoint"]

    auth = (client_id, client_secret)
    data = {"grant_type": "client_credentials", "scope": scope}
    r = requests.post(token_url, auth=auth, data=data)
    r.raise_for_status()
    return r.json()


def setup_auth():
    """
    Creates/retrieves Cognito authentication infrastructure.
    This is a one-time operation and only necessary if new auth with Cognito needs to be setup.

    Returns: dict with auth configuration needed for gateway setup
    """
    session = boto3.Session(region_name=AWS_REGION)
    cognito = session.client("cognito-idp")

    # 1) Create/retrieve Cognito user pool
    print("Creating/retrieving Cognito user pool...")
    user_pool_id = get_or_create_user_pool(cognito, COGNITO_USER_POOL_NAME)
    print(f"User pool id: {user_pool_id}")

    # 2) Create/retrieve resource server with scopes
    print("Creating/retrieving resource server...")
    scopes = [
        {"ScopeName": "gateway:read", "ScopeDescription": "Read access"},
        {"ScopeName": "gateway:write", "ScopeDescription": "Write access"}
    ]
    get_or_create_resource_server(cognito, user_pool_id, RESOURCE_SERVER_ID, RESOURCE_SERVER_NAME, scopes)

    # 3) Create/retrieve M2M client
    print("Creating/retrieving M2M client...")
    client_id, client_secret = get_or_create_m2m_client(cognito, user_pool_id, CLIENT_NAME, RESOURCE_SERVER_ID)
    print(f"Client ID: {client_id}")

    # 4) Build discovery URL
    discovery_url = f"https://cognito-idp.{AWS_REGION}.amazonaws.com/{user_pool_id}/.well-known/openid-configuration"
    print(f"Cognito discovery URL: {discovery_url}")

    auth_config = {
        "user_pool_id": user_pool_id,
        "client_id": client_id,
        "client_secret": client_secret,
        "resource_server_id": RESOURCE_SERVER_ID,
        "discovery_url": discovery_url,
        "jwt_authorizer_config": {
            "customJWTAuthorizer": {
                "allowedClients": [client_id],
                "discoveryUrl": discovery_url
            }
        }
    }

    return auth_config


if __name__ == "__main__":
    auth_config = setup_auth()
    print("\n✓ Authentication setup complete!")
    print("\nAuth configuration to pass to manage_gateway.py:")
    print(json.dumps({k: v for k, v in auth_config.items() if k != "client_secret"}, indent=2))


