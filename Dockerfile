# Example Reviewer API (Python 3.12 + .NET 8 SDK)
#
# Multi-stage build: copy the .NET SDK from the official image into a Python
# base image so the API can run compile-capable tools.

# ---- Stage 1: .NET SDK donor ----
# Digest resolved fresh from mcr.microsoft.com's registry API on 2026-08-30
# (TC-EPIC3-01/TC-EPIC3-02). Bump: re-resolve via
#   curl -s -H "Accept: application/vnd.docker.distribution.manifest.list.v2+json" \
#     https://mcr.microsoft.com/v2/dotnet/sdk/manifests/8.0-bookworm-slim -D - -o /dev/null \
#     | grep -i docker-content-digest
FROM mcr.microsoft.com/dotnet/sdk:9.0-bookworm-slim@sha256:f190d2dd9eef2899c91ac323caa0bd2b39334a5400ba93013e5199da39dad940 AS dotnet-sdk

# ---- Stage 2: Python runtime + .NET SDK ----
# Digest resolved fresh from Docker Hub's registry API on 2026-08-30. Bump:
#   TOKEN=$(curl -s "https://auth.docker.io/token?service=registry.docker.io&scope=repository:library/python:pull" | python3 -c "import json,sys;print(json.load(sys.stdin)['token'])")
#   curl -s -H "Authorization: Bearer $TOKEN" -H "Accept: application/vnd.docker.distribution.manifest.list.v2+json" \
#     https://registry-1.docker.io/v2/library/python/manifests/3.12-slim-bookworm -D - -o /dev/null \
#     | grep -i docker-content-digest
FROM python:3.12-slim-bookworm@sha256:0f5b26b9518d002b6173fd61daad821fa340635ebfec5bba471013f9ca114579

COPY --from=dotnet-sdk /usr/share/dotnet /usr/share/dotnet
RUN ln -s /usr/share/dotnet/dotnet /usr/local/bin/dotnet

ENV DOTNET_CLI_TELEMETRY_OPTOUT=1
ENV DOTNET_NOLOGO=1

# libicu is required by .NET; build tools are needed for native Python wheels.
COPY requirements.txt requirements-dev.txt /tmp/
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        libicu72 gcc libc6-dev zlib1g-dev && \
    pip install --no-cache-dir -r /tmp/requirements.txt && \
    apt-get purge -y --auto-remove gcc libc6-dev zlib1g-dev && \
    apt-get clean && rm -rf /var/lib/apt/lists/* /tmp/requirements*.txt

WORKDIR /app

COPY src/ ./src/
COPY config/ ./config/
COPY scripts/ ./scripts/
COPY tests/ ./tests/
COPY pytest.ini setup.py ./

RUN mkdir -p /app/data /app/workspace

RUN useradd --create-home appuser && chown -R appuser:appuser /app
USER appuser

EXPOSE 18800

HEALTHCHECK --interval=30s --timeout=5s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:18800/healthz')"

CMD ["python", "-m", "uvicorn", "src.http_server:app", "--host", "0.0.0.0", "--port", "18800"]
