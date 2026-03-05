FROM ghcr.io/mortenlj/mise-lib/python-builder:latest AS build

FROM ghcr.io/mortenlj/mise-lib/python-3.13:latest AS docker
ENTRYPOINT ["python", "-m", "ibidem.ibidem_api"]
