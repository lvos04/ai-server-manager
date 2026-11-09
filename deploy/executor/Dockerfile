# syntax=docker/dockerfile:1.7
# AI Server Manager — executor (eigen image, eigen Custom App 'ai-server-manager-executor', poort 30410).
#
#   docker build -f deploy/executor/Dockerfile [--secret id=ca_bundle,src=<ca.pem>] -t ai-server-manager-executor:dev .
#
# Fase P0: alleen healthz/readyz, een Nederlandse statuspagina 'nog niet gekoppeld' en een allowlist die alles weigert.
# Geen Docker-socket, geen shell-endpoint. Start als root alleen om /appdata aan 568:568 te geven; daarna als 568.

ARG PYTHON_IMAGE=docker.io/library/python:3.12.16-slim-bookworm@sha256:935c3c5b12357a7e10caa9c1e6ca5692344d97cf229832ef584be2cec9fc03df

FROM ${PYTHON_IMAGE} AS build
WORKDIR /src
COPY apps/executor/requirements.lock ./requirements.lock
RUN --mount=type=secret,id=ca_bundle,required=false \
    if [ -s /run/secrets/ca_bundle ]; then export PIP_CERT=/run/secrets/ca_bundle; fi; \
    pip install --no-cache-dir --disable-pip-version-check --root-user-action=ignore --prefix=/install \
        --no-deps -r requirements.lock
COPY apps/executor/pyproject.toml apps/executor/README.md ./
COPY apps/executor/src ./src
RUN --mount=type=secret,id=ca_bundle,required=false \
    if [ -s /run/secrets/ca_bundle ]; then export PIP_CERT=/run/secrets/ca_bundle; fi; \
    pip wheel --no-cache-dir --disable-pip-version-check --no-deps -w /wheels . \
    && pip install --no-cache-dir --disable-pip-version-check --root-user-action=ignore --prefix=/install --no-deps /wheels/executor-*.whl

FROM ${PYTHON_IMAGE}
ARG VERSION=0.1.0
ARG REVISION=onbekend
LABEL org.opencontainers.image.title="ai-server-manager-executor" \
      org.opencontainers.image.description="AI Server Manager — executor (fase P0: nog niet gekoppeld)" \
      org.opencontainers.image.source="https://github.com/lvos04/ai-server-manager" \
      org.opencontainers.image.version="${VERSION}" \
      org.opencontainers.image.revision="${REVISION}"
COPY --from=build /install /usr/local
COPY deploy/executor/entrypoint.py /usr/local/lib/executor/entrypoint.py
COPY deploy/executor/healthcheck.py /usr/local/lib/executor/healthcheck.py
RUN set -eu; groupadd -g 568 apps; useradd -u 568 -g 568 -M -d /tmp -s /usr/sbin/nologin apps; \
    mkdir -p /appdata; chown 568:568 /appdata; chmod 0750 /appdata; \
    python -m pip check; python -c "import executor.app"
ENV PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1 EXECUTOR_DATA_DIR=/appdata EXECUTOR_PORT=30410 TZ=Etc/UTC
VOLUME ["/appdata"]
EXPOSE 30410
HEALTHCHECK --interval=30s --timeout=8s --start-period=30s --retries=3 \
  CMD ["python", "/usr/local/lib/executor/healthcheck.py"]
# entrypoint.py geeft /appdata aan 568, wisselt naar 568 en vervangt zichzelf door de API (PID 1, geen root meer).
CMD ["python", "/usr/local/lib/executor/entrypoint.py"]
