FROM python:3.12-slim
ARG VERSION=0.6.0-draft.1
ARG REVISION=unknown
LABEL org.opencontainers.image.title="Punkti Node" \
      org.opencontainers.image.description="Self-hostable Punkti 0.6 draft Mesh node" \
      org.opencontainers.image.version=$VERSION \
      org.opencontainers.image.revision=$REVISION \
      org.opencontainers.image.source="https://github.com/Fisker1111/Punkto"
WORKDIR /app
COPY node/requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt
COPY punkti_node/ /app/punkti_node/
COPY node/entrypoint.py /entrypoint.py
# Build provenance is not an operator configuration override.
ENV PUNKTO_NODE_CONFIG=/config/punkto-node.yml
RUN printf '%s\n' "$VERSION" > /app/build-version && printf '%s\n' "$REVISION" > /app/build-revision
EXPOSE 8000
STOPSIGNAL SIGTERM
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
  CMD ["python", "-c", "from punkti_node.config import load_config; from urllib.request import urlopen; c=load_config(); h=c['network']['listen_host']; urlopen('http://'+('127.0.0.1' if h=='0.0.0.0' else h)+':'+str(c['network']['listen_port'])+'/health', timeout=3).close()"]
ENTRYPOINT ["python", "/entrypoint.py"]
