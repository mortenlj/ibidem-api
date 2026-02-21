import decimal
from typing import List, Optional

from pydantic import BaseModel


class WeatherResponse(BaseModel):
    icon_name: str
    temperature: decimal.Decimal


class ForecastData(BaseModel):
    air_temperature: Optional[decimal.Decimal] = None


class ForecastSummary(BaseModel):
    symbol_code: str


class ForecastHour(BaseModel):
    details: Optional[ForecastData] = None
    summary: Optional[ForecastSummary] = None


class ForecastTimeStep(BaseModel):
    instant: Optional[ForecastHour] = None
    next_1_hours: Optional[ForecastHour] = None


class ForecastTimeStepWrapper(BaseModel):
    data: ForecastTimeStep


class Forecast(BaseModel):
    timeseries: List[ForecastTimeStepWrapper]


class METJSONForecast(BaseModel):
    properties: Forecast
