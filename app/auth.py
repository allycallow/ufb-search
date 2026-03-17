from os import getenv

from fastapi import HTTPException, Security, status
from fastapi.security import APIKeyHeader

API_KEY = getenv("API_KEY")
api_key_header = APIKeyHeader(name="X-API-Key")


def verify_api_key(api_key_header: str = Security(api_key_header)):
    if not api_key_header or api_key_header != API_KEY:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing or invalid API key",
        )
