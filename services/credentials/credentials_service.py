"""
credentials_service.py
API key credential provider management.
"""
import os
import boto3
from botocore.exceptions import ClientError

AWS_REGION = os.environ.get("AWS_DEFAULT_REGION", "us-east-1")


def create_or_get_api_key_credential_provider(provider_name: str, api_key: str) -> str:
    """
    Create or retrieve an API key credential provider.

    Args:
        provider_name: Name of the credential provider
        api_key: The API key value

    Returns:
        Credential provider ARN

    Raises:
        ValueError: If credential provider with same name already exists
        ClientError: If AWS API call fails
    """
    session = boto3.Session(region_name=AWS_REGION)
    agentcore = session.client("bedrock-agentcore-control")

    print(f"Creating/retrieving credential provider: {provider_name}")
    try:
        resp = agentcore.create_api_key_credential_provider(
            name=provider_name,
            apiKey=api_key
        )
        credential_provider_arn = resp["credentialProviderArn"]
        print("✓ Credential provider created.")
    except ClientError as e:
        if "already exists" in str(e) or "EntityAlreadyExists" in str(e):
            print("✓ Credential provider already exists.")
            raise ValueError(
                f"Credential provider '{provider_name}' already exists. "
                "Please use a unique name or handle provider updates manually."
            )
        else:
            raise

    print(f"Credential provider ARN: {credential_provider_arn}")
    return credential_provider_arn

