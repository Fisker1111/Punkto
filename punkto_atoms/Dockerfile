# Build from repository root: docker build -f punkto_atoms/Dockerfile .
FROM python:3.12-slim
WORKDIR /app
COPY punkto_atoms/requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r requirements.txt
# Only geohash3d is needed; avoid the full core package's eager imports.
COPY core/geohash3d.py /app/core/geohash3d.py
RUN touch /app/core/__init__.py
COPY punkto_atoms /app/punkto_atoms
ENV PUNKTO_ATOMS_PORT=8020 PUNKTO_ATOMS_DB=/data/atoms.db
VOLUME ["/data"]
EXPOSE 8020
CMD ["python", "-m", "punkto_atoms"]
