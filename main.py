"""
main.py
Orchestrates the full setup: authentication, gateway, and tools.
This file demonstrates how to use the modular setup scripts together.
"""
import os
from auth import setup_auth
from gateway import setup_gateway
from tools import add_tool_to_gateway

# CONFIG: change these as needed
# This file demonstrates creating auth,  a gateway, and adding a tool BUT there is also a FastAPI API in api/main.py that can be used
# to create gateways and tools programmatically.
AWS_REGION = os.environ.get("AWS_DEFAULT_REGION", "us-east-1")
OPENAPI_PATH = "openapi_specs/nasa_mars_insights_openapi.json"
GATEWAY_NAME = "DemoGWOpenAPIAPIKeyNasaOAI"
TARGET_NAME = "DemoOpenAPITargetS3NasaMars"
NASA_API_KEY = os.environ.get("NASA_API_KEY", "abc")


def main():
    """
    Full setup workflow:
    1. Setup authentication (one-time, reusable)
    2. Setup gateway (creates IAM role and gateway, can be reused for multiple tools)
    3. Add tool to gateway (can add multiple tools to same gateway)
    """

    print("=" * 60)
    print("STEP 1: Setting up authentication")
    print("=" * 60)
    auth_config = setup_auth()

    # print("\n" + "=" * 60)
    # print("STEP 2: Setting up gateway")
    # print("=" * 60)
    # gateway_info = setup_gateway(
    #     gateway_name=GATEWAY_NAME,
    #     auth_config=auth_config,
    #     description="AgentCore Gateway with OpenAPI targets"
    # )
    #
    # print("\n" + "=" * 60)
    # print("STEP 3: Adding NASA Mars tool to gateway")
    #
    # print("\n" + "=" * 60)
    # print("STEP 3: Adding NASA Mars tool to gateway")
    # print("=" * 60)
    # response = add_tool_to_gateway(
    #     gateway_id=gateway_info["gateway_id"],
    #     target_name=TARGET_NAME,
    #     openapi_file_path=OPENAPI_PATH,
    #     api_key=NASA_API_KEY,
    #     api_key_provider_name="NasaInsightAPIKey",
    #     api_key_param_name="api_key",
    #     api_key_location="QUERY_PARAMETER",
    #     description="NASA Mars Insights API tool"
    # )
    #
    # print("\n" + "=" * 60)
    # print("✓ Setup complete!")
    # print("=" * 60)
    # print(f"\nGateway URL: {gateway_info['gateway_url']}")
    # print(f"Gateway ID: {gateway_info['gateway_id']}")
    # print(f"\nTo test:")
    print("1. Request a Cognito token using client credentials")
    print(f"   User Pool ID: {auth_config['user_pool_id']}")
    print(f"   Client ID: {auth_config['client_id']}")
    print(f"   Discovery URL: {auth_config['discovery_url']}")


if __name__ == "__main__":
    main()

