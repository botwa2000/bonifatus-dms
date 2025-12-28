# backend/Dockerfile
FROM python:3.11-slim

LABEL maintainer="bonifatus.app@gmail.com"
LABEL description="Bonifatus DMS - Production Document Management System"
LABEL version="1.0.0"

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONPATH="/app"
ENV PORT=8080

WORKDIR /app

# Create non-root user for security
RUN groupadd -r bonifatus && useradd -r -g bonifatus bonifatus

# Install system dependencies including Tesseract OCR, Hunspell, ClamAV, and libpostal
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        gcc \
        g++ \
        make \
        libc6-dev \
        curl \
        libmagic1 \
        tesseract-ocr \
        tesseract-ocr-eng \
        tesseract-ocr-deu \
        tesseract-ocr-rus \
        libtesseract-dev \
        poppler-utils \
        libglib2.0-0 \
        libsm6 \
        libxext6 \
        libxrender1 \
        libgomp1 \
        libgl1 \
        hunspell \
        libhunspell-dev \
        hunspell-en-us \
        hunspell-de-de \
        hunspell-ru \
        hunspell-fr \
        clamav \
        clamav-daemon \
        clamav-freshclam \
        autoconf \
        automake \
        libtool \
        pkg-config \
    && rm -rf /var/lib/apt/lists/*

# Install libpostal for address extraction (60+ countries, all languages)
# Using master branch as v1.1 has incompatible pointer type errors with modern GCC
RUN curl -L https://github.com/openvenues/libpostal/archive/refs/heads/master.tar.gz -o /tmp/libpostal.tar.gz \
    && cd /tmp \
    && tar -xzf libpostal.tar.gz \
    && cd libpostal-master \
    && ./bootstrap.sh \
    && ./configure --datadir=/usr/local/share/libpostal \
    && make -j$(nproc) \
    && make install \
    && ldconfig \
    && cd / \
    && rm -rf /tmp/libpostal-master /tmp/libpostal.tar.gz

# Configure ClamAV directories (root:root ownership for containerized deployment)
RUN mkdir -p /var/run/clamav /var/lib/clamav /var/log/clamav \
    && chmod 755 /var/log/clamav /var/run/clamav /var/lib/clamav

# Copy optimized ClamAV configurations
COPY clamd.conf /etc/clamav/clamd.conf
COPY freshclam.conf /etc/clamav/freshclam.conf

# Set proper permissions for ClamAV configs (root:root for containerized deployment)
RUN chmod 644 /etc/clamav/clamd.conf /etc/clamav/freshclam.conf

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt

# Download spaCy NER models for organization/person/location extraction
# These models enable entity extraction in multiple languages
RUN python -m spacy download de_core_news_md \
    && python -m spacy download en_core_web_md \
    && python -m spacy download fr_core_news_md \
    && python -m spacy download ru_core_news_md

# Copy application code
COPY app/ ./app/

# Copy scripts directory
COPY scripts/ ./scripts/

# Copy Alembic migration files
COPY alembic.ini .
COPY alembic/ ./alembic/

# Copy startup script
COPY start.sh /app/start.sh

# Copy healthcheck script
COPY healthcheck.sh /app/healthcheck.sh

# Create necessary directories and set permissions
RUN mkdir -p /app/logs /app/temp \
    && chown -R bonifatus:bonifatus /app \
    && chmod -R 755 /app \
    && chmod +x /app/start.sh \
    && chmod +x /app/healthcheck.sh

# Smart health check that works for both backend and celery-worker
# Backend: checks HTTP endpoint | Celery Worker: checks celery inspect ping
HEALTHCHECK --interval=30s --timeout=30s --start-period=5s --retries=3 \
    CMD /app/healthcheck.sh || exit 1

# Expose port 8080 for Cloud Run
EXPOSE 8080

# Use startup script that runs ClamAV and the app
CMD ["/app/start.sh"]