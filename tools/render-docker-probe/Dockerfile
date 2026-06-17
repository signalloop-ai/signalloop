FROM python:3.11-alpine

RUN apk add --no-cache docker-cli

WORKDIR /app

COPY app.py /app/app.py

RUN pip install --no-cache-dir fastapi==0.115.6 uvicorn[standard]==0.34.0

ENV PORT=10000

CMD ["sh", "-c", "uvicorn app:app --host 0.0.0.0 --port ${PORT:-10000}"]
