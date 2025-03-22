import logging
from functools import lru_cache
from pathlib import Path

import httpx
import joserfc.errors
from fastapi import APIRouter, Depends, HTTPException, status
from joserfc import jwt
from joserfc.jwk import KeySet
from joserfc.jwt import JWTClaimsRegistry
from joserfc.rfc7518.oct_key import OctKey
from lightkube import Client
from lightkube.models.authentication_v1 import TokenRequestSpec
from lightkube.models.meta_v1 import ObjectMeta
from lightkube.resources.core_v1 import ServiceAccountToken

from ibidem_api.api.v1.token.models import KubeConfig, TokenRequest, TokenResponse
from ibidem_api.core.config import DeploySubject, Mode, settings

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

CA_CRT_PATH = Path("/var/run/secrets/kubernetes.io/serviceaccount/ca.crt")
CLAIMS = JWTClaimsRegistry(
    iss={
        "essential": True,
        "value": "https://token.actions.githubusercontent.com",
    },
    aud={
        "essential": True,
        "value": "ibidem.no:deploy",
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
    if settings.mode == Mode.DEBUG:
        # Default key used on jwt.io
        return OctKey.import_key("a-string-secret-at-least-256-bits-long")
    resp = httpx.get("https://token.actions.githubusercontent.com/.well-known/jwks")
    resp.raise_for_status()
    key_set = KeySet.import_key_set(resp.json())
    return key_set


@lru_cache
def kube():
    return Client()


@lru_cache
def subjects():
    return {subject.repository: subject for subject in settings.deploy_subjects}


@lru_cache
def ca_crt() -> bytes:
    if CA_CRT_PATH.is_file():
        return CA_CRT_PATH.read_bytes()
    return b""


@router.post("/kubeconfig", status_code=status.HTTP_200_OK)
async def kubeconfig(
    data: TokenRequest,
    keyset: KeySet = Depends(github_keyset),
    kube: Client = Depends(kube),
    subjects: dict[str, DeploySubject] = Depends(subjects),
    ca_crt: str = Depends(ca_crt),
) -> KubeConfig:
    subject = await _validate_subject(data, keyset, subjects)
    k8s_token = await _get_k8s_token(kube, subject.service_account, subject.namespace)
    LOG.info(
        "Received k8s token for service account %r in namespace %r: %r",
        subject.service_account,
        subject.namespace,
        k8s_token,
    )
    return KubeConfig.make(ca_crt, k8s_token, settings.advertised_cluster_address)


@router.post("/", status_code=status.HTTP_200_OK)
async def token(
    data: TokenRequest,
    keyset: KeySet = Depends(github_keyset),
    kube: Client = Depends(kube),
    subjects: dict[str, DeploySubject] = Depends(subjects),
) -> TokenResponse:
    """Accept a JWT token and return a new kubernetes token"""
    subject = await _validate_subject(data, keyset, subjects)
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


async def _validate_subject(data, keyset, subjects):
    LOG.info("Received token: %r", data.token)
    try:
        token = jwt.decode(data.token, key=keyset)
    except ValueError as e:
        LOG.error("Error while decoding token", exc_info=True)
        raise HTTPException(status_code=400, detail=str(e))

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
        LOG.info("Token claims: %r", token.claims)
        raise HTTPException(status_code=400, detail=str(e))
    LOG.info("Received valid token for repository: %r", token.claims["repository"])
    subject = subjects.get(token.claims["repository"])
    if subject is None:
        LOG.error("No subject found for repository: %r", token.claims["repository"])
        raise HTTPException(status_code=404, detail="Repository not found")
    return subject


async def _get_k8s_token(kube, name, namespace):
    service_account_token = ServiceAccountToken(
        metadata=ObjectMeta(name=name, namespace=namespace),
        spec=TokenRequestSpec(audiences=[]),
    )
    service_account_token = kube.create(
        service_account_token, name=name, namespace=namespace
    )
    return service_account_token.status.token
