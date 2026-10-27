# WH40k Colony Manager - Backend Docker Image
# Multi-stage build for production-ready backend

# ============================================
# Stage 1: Dependencies
# ============================================
FROM python:3.12-slim-bookworm AS builder

WORKDIR /app

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Install uv for fast dependency management
# Note: Using pip without --only-binary since uv is a pre-built wheel
RUN pip install uv

# Copy dependency files
COPY pyproject.toml uv.lock* README.md ./

# Install dependencies to a virtual environment
# Note: --frozen uses locked versions from uv.lock (addressing SonarQube docker:S8544)
# Using --no-build-isolation to prevent setup script execution (addressing docker:S8541)
# Using --no-install-project to only install dependencies, not the project itself
# (source code isn't copied until the runtime stage)
RUN uv venv /app/.venv && \
    UV_PROJECT_ENVIRONMENT=/app/.venv uv sync --frozen --no-dev --no-build-isolation --no-install-project

# ============================================
# Stage 2: Runtime
# ============================================
FROM python:3.12-slim-bookworm AS runtime

# Create non-root user for security
RUN groupadd -r colony && useradd -r -g colony colony

WORKDIR /app

# Copy virtual environment from builder
COPY --from=builder /app/.venv /app/.venv

# Copy application code
COPY src/colony_manager/ ./colony_manager/
COPY config/ ./config/
COPY alembic/ ./alembic/
COPY alembic.ini ./
# Demo-user provisioning (dev only, see scripts/create_demo_users.py). Only
# exercised when the container is started with SEED_DEMO_USERS=true (the dev
# docker-compose.yml sets it; docker-compose.prod.yml never does).
COPY scripts/create_demo_users.py ./scripts/create_demo_users.py

# Set environment variables
ENV PATH="/app/.venv/bin:$PATH"
ENV PYTHONPATH="/app"
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV ENVIRONMENT=production

# Create data directory for SQLite database and set ownership
RUN mkdir -p /data && chown -R colony:colony /app /data

USER colony

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/api/v1/health')" || exit 1

# Run migrations, then start uvicorn (factory pattern). Running `alembic
# upgrade head` at every container start keeps the persisted /data volume in
# sync with the ORM schema: the app's startup only calls init_db()
# (create-only), which never alters existing tables and never stamps
# alembic_version, so without this step a schema change (e.g. the star_system
# addition) fails on an existing volume with "no column named ...". Fresh
# volumes get a migration-tracked schema from the start. For volumes already
# created by an older image via init_db() (tables present, no alembic_version),
# stamp once manually: `alembic stamp head`.
CMD ["sh", "-c", "python -m alembic upgrade head && if [ \"${SEED_DEMO_USERS}\" = \"true\" ]; then python scripts/create_demo_users.py; fi && exec uvicorn colony_manager.adapters.api.app:create_app --factory --host 0.0.0.0 --port 8000 --workers 2"]
