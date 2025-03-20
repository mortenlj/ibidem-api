import logging
from functools import lru_cache

import httpx
from fastapi import APIRouter, Depends, status
from joserfc import jwt
from joserfc.jwk import KeySet
from joserfc.jwt import JWTClaimsRegistry
from lightkube import Client
from lightkube.models.authentication_v1 import TokenRequest, TokenRequestSpec
from lightkube.models.meta_v1 import ObjectMeta
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
    token_request = TokenRequest(
        apiVersion="authentication.k8s.io/v1",
        kind="TokenRequest",
        metadata=ObjectMeta(
            name=name,
            namespace=namespace,
        ),
        spec=TokenRequestSpec(audiences=[]),
    )
    req = kube._client._client.build_request(
        "POST",
        f"/api/v1/namespaces/{namespace}/serviceaccounts/{name}/token",
        json=token_request.to_dict(),
    )
    resp = kube._client.send(req)
    resp.raise_for_status()
    token_request = TokenRequest.from_dict(resp.json())
    return token_request.status.token
