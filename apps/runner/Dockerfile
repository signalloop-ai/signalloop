FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

RUN python -m pip install --no-cache-dir \
    boto3==1.35.90 \
    pytest==8.3.4

WORKDIR /app
COPY signalloop_runner /app/signalloop_runner

ENTRYPOINT ["python", "-m", "signalloop_runner.main"]
