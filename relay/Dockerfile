# ── Punkto Relay — Docker image ──────────────────────────────────────────────
# Single-file Python relay node.
# Data is stored on a volume at /data so atoms survive container restarts.
#
# Build:
#   docker build -t punkto-relay ./relay
#
# Run (standalone, for development):
#   docker run -p 8000:8000 -v $(pwd)/data:/data punkto-relay
#
# In production use docker-compose — see deploy/
# ─────────────────────────────────────────────────────────────────────────────

FROM python:3.12-slim

LABEL org.opencontainers.image.title="Punkto Relay"
LABEL org.opencontainers.image.source="https://github.com/Fisker1111/Punkto"
LABEL org.opencontainers.image.description="Punkto relay node — accepts and replicates atoms"

WORKDIR /app

# Install Python dependencies first (layer cache-friendly)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy relay source
COPY relay.py .

# Data directory — always mount as a named volume to persist atoms
RUN mkdir -p /data

# Environment defaults — all can be overridden via docker-compose env or .env
ENV PUNKTO_HOST=0.0.0.0
ENV PUNKTO_PORT=8000
ENV PUNKTO_DATA_DIR=/data
ENV PUNKTO_NODE_NAME=punkto-relay
ENV PUNKTO_PEERS=""
ENV PUNKTO_BUFFER_ATOMS=10000
ENV PUNKTO_BUFFER_HOURS=168
ENV PUNKTO_SYNC_INTERVAL=30

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')" || exit 1

CMD ["python", "relay.py"]
