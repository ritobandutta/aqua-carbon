# AquaCarbon DC — Commons Edition (v2)
# Production Container for Google Cloud Run (Downscale-to-Zero & Fast Startup)

FROM python:3.10-slim

# Prevent Python from writing .pyc and buffer stdout/stderr
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PORT=8080

WORKDIR /app

# Install minimal build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy and install Python requirements
COPY requirements.txt /app/
RUN pip install --no-cache-dir -r requirements.txt

# Copy application source code
COPY engine/ /app/engine/
COPY agents/ /app/agents/
COPY evals/ /app/evals/
COPY api/ /app/api/
COPY static/ /app/static/
COPY tests/ /app/tests/
COPY SPEC.md /app/

# Expose Cloud Run default port
EXPOSE 8080

# Health check
HEALTHCHECK --interval=30s --timeout=5s --start-period=5s --retries=3 \
  CMD curl -f http://localhost:${PORT}/api/health || exit 1

# Launch FastAPI app with dynamic port substitution for Cloud Run
CMD exec uvicorn api.main:app --host 0.0.0.0 --port ${PORT}
