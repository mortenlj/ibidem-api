import decimal
import logging
import tempfile
from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import FileResponse
from hishel.httpx import AsyncCacheClient

from ibidem.ibidem_api import get_version
from ibidem.ibidem_api.api.v1.weather.models import WeatherResponse, METJSONForecast
from ibidem.ibidem_api.core.config import settings

LOG = logging.getLogger(__name__)

ICON_BASE_URL = "https://raw.githubusercontent.com/metno/weathericons/refs/heads/main/weather/png/"
ICON_BASE_DIRECTORY = Path(tempfile.gettempdir()) / "weather_icons"

NOWCAST_URL = "https://api.met.no/weatherapi/nowcast/2.0/complete"

tags_metadata = [
    {
        "name": "weather",
        "description": "Endpoints can be used from esphome to fetch current weather data",
    }
]

router = APIRouter(
    tags=["weather"],
)


async def http_client():
    headers = {"user-agent": f"ibidem-api/{get_version()} +https://github.com/mortenlj/ibidem-api"}
    async with AsyncCacheClient(follow_redirects=True, headers=headers) as client:
        yield client


@router.get("/", status_code=status.HTTP_200_OK)
async def weather(http_client: Annotated[AsyncCacheClient, Depends(http_client)]) -> WeatherResponse:
    LOG.info("Looking up weather for %s", settings.forecast_location)
    params = {
        "lat": round(settings.forecast_location.latitude, 4),
        "lon": round(settings.forecast_location.longtitude, 4),
        "altitude": settings.forecast_location.altitude
    }
    resp = await http_client.get(NOWCAST_URL, params=params)
    resp.raise_for_status()
    data = resp.json()
    forecast = METJSONForecast.model_validate(data)
    forecast_instant = forecast.properties.timeseries[0]
    icon_name = forecast_instant.data.next_1_hours.summary.symbol_code
    temperature = forecast_instant.data.instant.details.air_temperature
    return WeatherResponse(icon_name=icon_name, temperature=temperature)


@router.get("/icon/{icon_name}", status_code=status.HTTP_200_OK, response_class=FileResponse)
async def retrieve_icon(icon_name, http_client: Annotated[AsyncCacheClient, Depends(http_client)]) -> Path:
    icon_filename = f"{icon_name}.png"
    icon_path = ICON_BASE_DIRECTORY / icon_filename
    if not icon_path.exists():
        icon_path.parent.mkdir(parents=True, exist_ok=True)
        icon_url = f"{ICON_BASE_URL}/{icon_filename}"
        resp = await http_client.get(icon_url)
        if resp.status_code == status.HTTP_404_NOT_FOUND:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
        resp.raise_for_status()
        tmp = tempfile.NamedTemporaryFile("wb", delete=False, dir=icon_path.parent)
        tmp_path = Path(tmp.name)
        with tmp as fobj:
            async for chunk in resp.aiter_bytes():
                fobj.write(chunk)
        tmp_path.rename(icon_path)
    return icon_path
