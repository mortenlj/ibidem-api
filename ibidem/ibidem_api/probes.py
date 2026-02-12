import logging

from fastapi import APIRouter, status

LOG = logging.getLogger(__name__)

tags_metadata = [
    {"name": "probes", "description": "Health and readiness probes"},
]

router = APIRouter(
    responses={status.HTTP_404_NOT_FOUND: {"detail": "Not found"}},
    tags=["probes"],
)


@router.get("/healthy", status_code=status.HTTP_200_OK)
def liveness():
    return "Healthy as a fish"


@router.get("/ready", status_code=status.HTTP_200_OK)
def readiness():
    return "Ready as an egg"
