import logging

from fastapi import APIRouter, Request, status
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


class Jwt(BaseModel):
    token: str


@router.get("/", status_code=status.HTTP_200_OK)
async def token_get(jwt: Jwt):
    """Accept a JWT token and return a new kubernetes token"""
    LOG.info(f"Received token:\n{jwt.token}")
    return {"token":"get"}

@router.post("/", status_code=status.HTTP_200_OK)
async def token_post(jwt: Jwt):
    """Accept a JWT token and return a new kubernetes token"""
    LOG.info(f"Received token:\n{jwt.token}")
    return {"token":"post"}
