# Build from repository root: docker build -f punkto_atoms/Dockerfile .
FROM python:3.12-slim
WORKDIR /app
COPY punkto_atoms/requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r requirements.txt
COPY core /app/core
COPY punkto_atoms /app/punkto_atoms
ENV PUNKTO_ATOMS_PORT=8020 PUNKTO_ATOMS_DB=/data/atoms.db
VOLUME ["/data"]
EXPOSE 8020
CMD ["python", "-m", "punkto_atoms"]
