import logging
from pprint import pformat

import httpx
from fastapi import APIRouter, status, Request
from fastapi.responses import RedirectResponse, JSONResponse

LOG = logging.getLogger(__name__)
DIETPI_VERSION_URL = "https://raw.githubusercontent.com/MichaIng/DietPi/refs/heads/master/.update/version"

tags_metadata = [
    {
        "name": "suc",
        "description": "Endpoints to be used with the Rancher [system-update-controller](https://github.com/rancher/system-upgrade-controller)",
    }
]

router = APIRouter(
    tags=["suc"],
)


@router.get("/dietpi",
            response_class=RedirectResponse,
            status_code=status.HTTP_302_FOUND,
            responses={
                status.HTTP_503_SERVICE_UNAVAILABLE: {
                    "description": "DietPi version URL is not available",
                    "model": str,
                },
            })
async def dietpi(req: Request):
    """Version redirect for Dietpi

    Interrogates the DietPi version URL, and create a redirect to a URL with the version
    as the last component of the path, such that it can be used by suc."""
    resp = httpx.get(DIETPI_VERSION_URL)
    try:
        resp.raise_for_status()
    except httpx.HTTPStatusError as e:
        return JSONResponse("Failed to get version information from DietPi",
                            status_code=status.HTTP_503_SERVICE_UNAVAILABLE)
    data = resp.text
    major, minor, patch = (0, 0, 0)
    for line in data.splitlines(keepends=False):
        if line.startswith("G_REMOTE_VERSION_CORE="):
            major = int(line.split("=")[1])
        elif line.startswith("G_REMOTE_VERSION_SUB="):
            minor = int(line.split("=")[1])
        elif line.startswith("G_REMOTE_VERSION_RC="):
            patch = int(line.split("=")[1])
    target = req.url_for("dietpi_version", version=f"{major}.{minor}.{patch}")

    LOG.info("HEADERS: %s", pformat(req.headers))

    return str(target)


@router.get("/dietpi/{version}", status_code=status.HTTP_200_OK)
async def dietpi_version(version: str):
    """This endpoint is not actually used, but is here to create a target URL for SUC"""
    return {"version": version}
