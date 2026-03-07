ARG PY_VERSION
FROM ghcr.io/mortenlj/mise-lib/python-builder:latest AS build

FROM ghcr.io/mortenlj/mise-lib/python-${PY_VERSION}:latest AS docker
ENTRYPOINT ["python", "-m", "ibidem.ibidem_api"]
