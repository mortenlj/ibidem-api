import logging
from functools import lru_cache

import httpx
from fastapi import APIRouter, Depends, status
from joserfc import jwt
from joserfc.jwk import KeySet
from joserfc.jwt import JWTClaimsRegistry
from pydantic import BaseModel

LOG = logging.getLogger(__name__)


tags_metadata = [
    {
        "name": "token",
        "description": "Endpoints that will provide a token when provided with a valid JWT",
    }
]

router = APIRouter(
    tags=["token"],
)


class TokenInput(BaseModel):
    token: str


CLAIMS = JWTClaimsRegistry(
    iss={
        "essential": True,
        "value": "https://token.actions.githubusercontent.com",
    },
    aud={
        "essential": True,
        "value": "api.ibidem.no:deploy",
    },
    repository={
        "essential": True,
    },
    ref={
        "essential": True,
        "value": "refs/heads/main",
    },
)


@lru_cache
def github_keyset():
    resp = httpx.get("https://token.actions.githubusercontent.com/.well-known/jwks")
    resp.raise_for_status()
    return KeySet.import_key_set(resp.json())


@router.post("/", status_code=status.HTTP_200_OK)
async def token(data: TokenInput, keyset: KeySet = Depends(github_keyset)):
    """Accept a JWT token and return a new kubernetes token"""
    token = jwt.decode(data.token, key=keyset)
    CLAIMS.validate(token.claims)
    LOG.info("Received valid token for repository: %r", token.claims["repository"])
    return {"token": "valid"}
