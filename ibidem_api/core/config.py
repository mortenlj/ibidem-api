from enum import Enum

from pydantic_settings import BaseSettings, SettingsConfigDict


class Mode(str, Enum):
    DEBUG = "Debug"
    RELEASE = "Release"


class Settings(BaseSettings):
    mode: Mode = Mode.DEBUG
    bind_address: str = "127.0.0.1"
    port: int = 3000
    root_path: str = ""

    model_config = SettingsConfigDict(env_nested_delimiter="__")

    @property
    def debug(self):
        return self.mode == Mode.DEBUG


settings = Settings()
