import decimal
import logging
from enum import Enum
from typing import Any, Optional, Tuple, Type

from pydantic import BaseModel, FilePath
from pydantic_settings import BaseSettings, SettingsConfigDict, YamlConfigSettingsSource
from pydantic_settings.sources import PydanticBaseSettingsSource
from watchfiles import awatch

LOG = logging.getLogger(__name__)


class SubjectLoaderSource(YamlConfigSettingsSource):
    def __call__(self) -> dict[str, Any]:
        file_path = self.current_state.get("deploy_subjects_path")
        if file_path is not None:
            self.yaml_file_path = file_path
            self.yaml_data = self._read_files(file_path)
            self.init_kwargs = self.yaml_data
        return super().__call__()


class Mode(str, Enum):
    DEBUG = "Debug"
    RELEASE = "Release"


class DeploySubject(BaseModel):
    repository: str
    namespace: str
    service_account: str


class ForecastLocation(BaseModel):
    latitude: decimal.Decimal
    longtitude: decimal.Decimal
    altitude: decimal.Decimal


class Settings(BaseSettings):
    mode: Mode = Mode.DEBUG
    bind_address: str = "127.0.0.1"
    port: int = 3000
    advertised_cluster_address: str = "http://localhost:8001"
    root_path: str = ""

    forecast_location: Optional[ForecastLocation] = None

    deploy_subjects_path: Optional[FilePath] = None
    deploy_subjects: list[DeploySubject] = []

    model_config = SettingsConfigDict(env_nested_delimiter="__")

    @property
    def debug(self):
        return self.mode == Mode.DEBUG

    @classmethod
    def settings_customise_sources(
        cls,
        settings_cls: Type[BaseSettings],
        init_settings: PydanticBaseSettingsSource,
        env_settings: PydanticBaseSettingsSource,
        dotenv_settings: PydanticBaseSettingsSource,
        file_secret_settings: PydanticBaseSettingsSource,
    ) -> Tuple[PydanticBaseSettingsSource, ...]:
        return (
            init_settings,
            env_settings,
            file_secret_settings,
            SubjectLoaderSource(settings_cls),
        )


async def watch_config():
    if settings.deploy_subjects_path:
        async for _ in awatch(settings.deploy_subjects_path):
            settings.__init__()
            LOG.info(f"Reloaded configuration {settings}")


settings = Settings()

if __name__ == "__main__":
    from pprint import pprint

    pprint(settings.model_dump_json())
