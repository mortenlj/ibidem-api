import logging

from fastapi import APIRouter, Request, status

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


@router.get("/", status_code=status.HTTP_200_OK)
async def token(req: Request, token: str):
    """Accept a JWT token and return a new kubernetes token"""
    LOG.info(f"Received token:\n{token}")
    return {"token":"stuff"}
