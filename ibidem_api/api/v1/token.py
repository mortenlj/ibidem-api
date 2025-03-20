import logging
from functools import lru_cache

import httpx
import joserfc.errors
from fastapi import APIRouter, Depends, HTTPException, status
from joserfc import jwt
from joserfc.jwk import KeySet
from joserfc.jwt import JWTClaimsRegistry
from lightkube import Client
from lightkube.models.authentication_v1 import TokenRequestSpec
from lightkube.models.meta_v1 import ObjectMeta
from lightkube.resources.core_v1 import ServiceAccountToken
from pydantic import BaseModel

from ibidem_api.core.config import DeploySubject, settings

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


class TokenRequest(BaseModel):
    token: str


class TokenResponse(BaseModel):
    token: str
    service_account: str
    namespace: str


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


@lru_cache
def kube():
    return Client()


@lru_cache
def subjects():
    return {subject.repository: subject for subject in settings.deploy_subjects}


@router.post("/", status_code=status.HTTP_200_OK)
async def token(
    data: TokenRequest,
    keyset: KeySet = Depends(github_keyset),
    kube: Client = Depends(kube),
    subjects: dict[str, DeploySubject] = Depends(subjects),
):
    """Accept a JWT token and return a new kubernetes token"""
    token = jwt.decode(data.token, key=keyset)
    try:
        CLAIMS.validate(token.claims)
    except joserfc.errors.ExpiredTokenError:
        LOG.warning(
            "Received expired token for repository: %r", token.claims["repository"]
        )
        raise HTTPException(status_code=401, detail="Token has expired")
    except joserfc.errors.JoseError as e:
        LOG.error(
            "Error while validating claims for repository %r",
            token.claims["repository"],
            exc_info=True,
        )
        raise HTTPException(status_code=400, detail=str(e))
    LOG.info("Received valid token for repository: %r", token.claims["repository"])
    subject = subjects.get(token.claims["repository"])
    if subject is None:
        LOG.error("No subject found for repository: %r", token.claims["repository"])
        raise HTTPException(status_code=404, detail="Repository not found")
    k8s_token = await _get_k8s_token(kube, subject.service_account, subject.namespace)
    LOG.info(
        "Received k8s token for service account %r in namespace %r: %r",
        subject.service_account,
        subject.namespace,
        k8s_token,
    )
    return TokenResponse(
        token=k8s_token,
        service_account=subject.service_account,
        namespace=subject.namespace,
    )


async def _get_k8s_token(kube, name, namespace):
    service_account_token = ServiceAccountToken(
        metadata=ObjectMeta(name=name, namespace=namespace),
        spec=TokenRequestSpec(audiences=[]),
    )
    service_account_token = kube.create(
        service_account_token, name=name, namespace=namespace
    )
    return service_account_token.status.token
