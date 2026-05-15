# ── Punkto PWA — Docker image (Caddy web server) ─────────────────────────────
# Serves the static PWA files.
# Caddy handles TLS automatically via Let's Encrypt.
#
# The Caddyfile is NOT baked into the image — it is mounted per node so that
# each node can specify its own domain without rebuilding.
#
# Build:
#   docker build -t punkto-web ./pwa
#
# In production use docker-compose — see deploy/
# ─────────────────────────────────────────────────────────────────────────────

FROM caddy:2-alpine

LABEL org.opencontainers.image.title="Punkto Web"
LABEL org.opencontainers.image.source="https://github.com/Fisker1111/Punkto"
LABEL org.opencontainers.image.description="Punkto PWA — served by Caddy with auto-TLS"

# Copy all static PWA assets into Caddy's default web root
COPY . /srv

# Remove the Dockerfile from the served files
RUN rm -f /srv/Dockerfile

# Caddyfile is mounted at runtime via docker-compose volume:
#   - ./Caddyfile:/etc/caddy/Caddyfile
# This keeps domain config out of the image.

EXPOSE 80 443

# Caddy is the default entrypoint — no CMD needed
