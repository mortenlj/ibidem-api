#!/usr/bin/env python
import logging
import signal

import sys
import uvicorn
from fastapi import FastAPI

from ibidem_api import probes, api, VERSION
from ibidem_api.core.config import settings
from ibidem_api.core.logging import get_log_config

LOG = logging.getLogger(__name__)
TITLE = "Ibidem micro APIs"


class ExitOnSignal(Exception):
    pass


tags_metadata = []
tags_metadata.extend(probes.tags_metadata)
tags_metadata.extend(api.tags_metadata)


app = FastAPI(
    title=TITLE,
    openapi_tags=tags_metadata,
    version=VERSION,
)
app.include_router(probes.router, prefix="/_")
app.include_router(api.router, prefix="/api")


def main():
    log_level = logging.DEBUG if settings.debug else logging.INFO
    log_format = "plain"
    exit_code = 0
    for sig in (signal.SIGTERM, signal.SIGINT):
        signal.signal(sig, signal_handler)
    try:
        print(f"Starting {TITLE} with configuration {settings}")
        uvicorn.run(
            "ibidem_api.main:app",
            host=settings.bind_address,
            port=settings.port,
            proxy_headers=True,
            root_path=settings.root_path,
            log_config=get_log_config(log_format, log_level),
            log_level=log_level,
            reload=settings.debug,
            access_log=settings.debug,
        )
    except ExitOnSignal:
        pass
    except Exception as e:
        print(f"unwanted exception: {e}")
        exit_code = 113
    return exit_code


def signal_handler(signum, frame):
    raise ExitOnSignal()


if __name__ == "__main__":
    sys.exit(main())
