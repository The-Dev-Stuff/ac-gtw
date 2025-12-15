"""
validations.py
Request validation logic for API endpoints.
"""
from fastapi import HTTPException, status
from api.models import Auth


def validate_auth(auth: Auth = None) -> None:
    """
    Validate auth object if provided.
    If auth was not provide, this function returns early, so execution can continue.

    If auth is provided with type 'api_key', ensures required fields are present.

    Args:
        auth: Optional Auth object to validate

    Raises:
        HTTPException: 400 Bad Request if validation fails
    """
    if not auth or auth.type != "api_key":
        return

    if not auth.config.api_key:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="api_key is required in auth.config when auth.type is 'api_key'"
        )

    if not auth.provider_name:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="auth.provider_name is required when auth.type is 'api_key'"
        )

