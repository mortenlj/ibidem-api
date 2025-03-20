import logging
from functools import lru_cache

import httpx
from fastapi import APIRouter, Depends, status
from joserfc import jwt
from joserfc.jwk import KeySet
from joserfc.jwt import JWTClaimsRegistry
from lightkube import Client
from lightkube.models.authentication_v1 import TokenRequestSpec
from lightkube.models.meta_v1 import ObjectMeta
from lightkube.resources.core_v1 import ServiceAccountToken
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

SUBJECTS = {
    "mortenlj/javazone": {
        "namespace": "default",
        "service_account": "deploy-javazone",
    }
}


@lru_cache
def github_keyset():
    resp = httpx.get("https://token.actions.githubusercontent.com/.well-known/jwks")
    resp.raise_for_status()
    return KeySet.import_key_set(resp.json())


@lru_cache
def kube():
    return Client()


@router.post("/", status_code=status.HTTP_200_OK)
async def token(
    data: TokenInput,
    keyset: KeySet = Depends(github_keyset),
    kube: Client = Depends(kube),
):
    """Accept a JWT token and return a new kubernetes token"""
    token = jwt.decode(data.token, key=keyset)
    CLAIMS.validate(token.claims)
    LOG.info("Received valid token for repository: %r", token.claims["repository"])
    namespace = "default"
    name = "deploy-javazone"
    k8s_token = await _get_k8s_token(kube, name, namespace)
    LOG.info(
        "Received k8s token for service account %r in namespace %r: %r",
        name,
        namespace,
        k8s_token,
    )
    return {"token": "valid"}


async def _get_k8s_token(kube, name, namespace):
    service_account_token = ServiceAccountToken(
        metadata=ObjectMeta(name=name, namespace=namespace),
        spec=TokenRequestSpec(audiences=[]),
    )
    service_account_token = kube.create(
        service_account_token, name=name, namespace=namespace
    )
    return service_account_token.status.token
