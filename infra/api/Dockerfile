FROM python:3.12-slim

# curl for healthcheck.  WeasyPrint needs cairo / pango / gdk-pixbuf plus
# fonts so PDFs render with consistent typography even when the host has no
# other fonts installed.
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        curl \
        libpango-1.0-0 \
        libpangoft2-1.0-0 \
        libcairo2 \
        libgdk-pixbuf-2.0-0 \
        libharfbuzz-subset0 \
        libffi8 \
        shared-mime-info \
        fonts-dejavu-core \
        fonts-liberation \
    && rm -rf /var/lib/apt/lists/*

# Install uv from official image
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

WORKDIR /app/apps/api

# Copy manifests only — deps cached separately from source code
COPY apps/api/pyproject.toml apps/api/alembic.ini ./

# Install all deps (including dev) into project-local .venv
# Source code will be bind-mounted; .venv stays in image layer
RUN uv sync

ENV PATH="/app/apps/api/.venv/bin:$PATH"

EXPOSE 8000

# Source dirs are bind-mounted for hot reload
CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]
