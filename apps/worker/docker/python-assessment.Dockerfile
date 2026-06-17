FROM python:3.11-slim

RUN python -m pip install --no-cache-dir \
    fastapi==0.115.6 \
    httpx==0.27.2 \
    pytest==8.3.4 \
    uvicorn==0.34.0

WORKDIR /workspace
