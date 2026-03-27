FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV OUTBOUND_HTTP_CA_BUNDLE=/etc/ssl/certs/ca-certificates.crt

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends build-essential default-libmysqlclient-dev curl ca-certificates \
    && rm -rf /var/lib/apt/lists/*

COPY . /app
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir .
