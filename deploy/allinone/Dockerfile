# syntax=docker/dockerfile:1.7
# AI Server Manager — Hub, ALLES-IN-ÉÉN image (PostgreSQL 16 + API + worker + AI-runner-stub [+ web-UI later]).
#
#   docker build -f deploy/allinone/Dockerfile [--secret id=ca_bundle,src=<ca.pem>] -t ai-server-manager:dev .
#
# Installatie: gewone TrueNAS Custom App (zie deploy/truenas/CUSTOM_APP.md): image ghcr.io/lvos04/ai-server-manager:<versie>,
# één Host Path → /appdata, poort 30400. Geen YAML, geen wachtwoorden, geen verplichte omgevingsvariabelen.
# PostgreSQL draait intern op een unix-socket (geen netwerkpoort, geen wachtwoord). De container start als root alleen
# om /appdata-submappen aan 568:568 te geven; daarna draait alles als 568 (AI-runner als aparte gebruiker 569).
# Base-images op exacte versie én @sha256-digest (nooit latest). De optionele BuildKit-secret 'ca_bundle' is alleen
# nodig achter een TLS-onderscheppende proxy; in GitHub Actions wordt hij niet meegegeven.

ARG PYTHON_IMAGE=docker.io/library/python:3.12.16-slim-bookworm@sha256:935c3c5b12357a7e10caa9c1e6ca5692344d97cf229832ef584be2cec9fc03df
ARG POSTGRES_IMAGE=docker.io/library/postgres:16.15-bookworm@sha256:5264710be20f409750ac6dc4e5706dcef929c87e241605463f0f9aefa932a8d9

# ---------------------------------------------------------------- PostgreSQL 16 server + client
FROM ${POSTGRES_IMAGE} AS pg
RUN set -eu; mkdir -p /out/lib /out/pg; \
    rm -f /usr/lib/postgresql/16/lib/llvmjit*.so; rm -rf /usr/lib/postgresql/16/lib/bitcode; \
    for f in /usr/lib/postgresql/16/bin/* /usr/lib/postgresql/16/lib/*.so; do ldd "$f" 2>/dev/null || true; done \
      | awk '/=>/ {print $3}' | sort -u \
      | grep -vE '/(libc|libm|libdl|libpthread|librt|libresolv|ld-linux[^/]*)\.so' \
      | while read -r lib; do cp -L "$lib" /out/lib/; done; \
    cp -rL /usr/lib/postgresql/16 /out/pg/lib; cp -rL /usr/share/postgresql/16 /out/pg/share; \
    test -f /out/pg/share/postgresql.conf.sample

# ---------------------------------------------------------------- Python: Hub-pakket + exact vastgezette afhankelijkheden
FROM ${PYTHON_IMAGE} AS build
WORKDIR /src
COPY apps/api/requirements.lock ./requirements.lock
RUN --mount=type=secret,id=ca_bundle,required=false \
    if [ -s /run/secrets/ca_bundle ]; then export PIP_CERT=/run/secrets/ca_bundle; fi; \
    pip install --no-cache-dir --disable-pip-version-check --root-user-action=ignore --prefix=/install \
        --no-deps -r requirements.lock
COPY apps/api/pyproject.toml apps/api/README.md ./
COPY apps/api/src ./src
COPY apps/api/alembic ./alembic
RUN --mount=type=secret,id=ca_bundle,required=false \
    if [ -s /run/secrets/ca_bundle ]; then export PIP_CERT=/run/secrets/ca_bundle; fi; \
    pip wheel --no-cache-dir --disable-pip-version-check --no-deps -w /wheels . \
    && pip install --no-cache-dir --disable-pip-version-check --root-user-action=ignore --prefix=/install --no-deps /wheels/hub-*.whl

# ---------------------------------------------------------------- PLEK VOOR DE WEB-UI (volgende agent)
# Voeg hier een stage 'web' toe (Next.js standalone, Node 22 op exacte versie + @sha256-digest), bv.:
#   FROM ${NODE_IMAGE} AS web
#   WORKDIR /src
#   COPY apps/web/package.json apps/web/package-lock.json ./
#   RUN --mount=type=secret,id=ca_bundle,required=false ... npm ci --ignore-scripts
#   COPY apps/web/ ./
#   RUN npm run build   # output: .next/standalone met server.js
# en in de runtime-stage hieronder (zie de gemarkeerde COPY-regels):
#   COPY --from=web /usr/local/bin/node /usr/local/bin/node
#   COPY --from=web /src/.next/standalone /opt/hub-web
#   COPY --from=web /src/.next/static /opt/hub-web/.next/static
# supervisor.py start de web-UI automatisch op poort 30400 zodra /opt/hub-web/server.js bestaat; de API luistert dan
# alleen op 127.0.0.1:8400 (HUB_API_URL voor de web-UI) en de healthcheck controleert beide.

# ---------------------------------------------------------------- runtime
FROM ${PYTHON_IMAGE}
ARG VERSION=0.1.0
ARG REVISION=onbekend
LABEL org.opencontainers.image.title="ai-server-manager" \
      org.opencontainers.image.description="AI Server Manager — Hub, alles-in-één (database, API, worker, AI-runner)" \
      org.opencontainers.image.source="https://github.com/lvos04/ai-server-manager" \
      org.opencontainers.image.version="${VERSION}" \
      org.opencontainers.image.revision="${REVISION}"
COPY --from=pg /out/pg/lib /usr/lib/postgresql/16
COPY --from=pg /out/pg/share /usr/share/postgresql/16
COPY --from=pg /out/lib /opt/pglibs
COPY --from=build /install /usr/local
# >>> web-UI (volgende agent): COPY --from=web ... (zie hierboven)
COPY deploy/allinone/supervisor.py /usr/local/lib/hub/supervisor.py
COPY deploy/allinone/healthcheck.py /usr/local/lib/hub/healthcheck.py
RUN set -eu; \
    for b in postgres initdb pg_ctl pg_isready psql pg_dump pg_restore; do \
      printf '#!/bin/sh\nLD_LIBRARY_PATH=/opt/pglibs exec /usr/lib/postgresql/16/bin/%s "$@"\n' "$b" > /usr/local/bin/$b; \
      chmod 0755 /usr/local/bin/$b; \
    done; \
    postgres --version | grep -q ' 16\.'; pg_dump --version | grep -q ' 16\.'; pg_restore --version | grep -q ' 16\.'; \
    groupadd -g 568 apps; useradd -u 568 -g 568 -M -d /tmp -s /usr/sbin/nologin apps; \
    groupadd -g 569 asm-ai; useradd -u 569 -g 569 -M -d /tmp -s /usr/sbin/nologin asm-ai; \
    mkdir -p /appdata; chown 568:568 /appdata; chmod 0750 /appdata; \
    python -m pip check; \
    python -c "import hub.app, hub.worker, psycopg, uvicorn, cryptography, websockets"; \
    python -c "from hub.migrations import script_location as s; print('migraties:', s())"
ENV PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1 \
    HUB_DATA_DIR=/appdata HUB_PORT=30400 TZ=Etc/UTC
VOLUME ["/appdata"]
EXPOSE 30400
HEALTHCHECK --interval=30s --timeout=8s --start-period=90s --retries=3 \
  CMD ["python", "/usr/local/lib/hub/healthcheck.py"]
# De bewaker is zelf PID 1 (signalen + zombie-opruiming) en draait na de init als 568: geen root-proces meer.
CMD ["python", "/usr/local/lib/hub/supervisor.py"]
