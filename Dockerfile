# Example Reviewer API (Python 3.12 + .NET 8 SDK)
#
# Multi-stage build: copy the .NET SDK from the official image into a Python
# base image so the API can run compile-capable tools.

# ---- Stage 1: .NET SDK donor ----
FROM mcr.microsoft.com/dotnet/sdk:8.0-bookworm-slim AS dotnet-sdk

# ---- Stage 2: Python runtime + .NET SDK ----
FROM python:3.12-slim-bookworm

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
