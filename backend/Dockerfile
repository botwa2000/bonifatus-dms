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

# Install system dependencies including Tesseract OCR and ClamAV
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        gcc \
        g++ \
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
        clamav \
        clamav-daemon \
        clamav-freshclam \
    && rm -rf /var/lib/apt/lists/*

# Configure ClamAV
RUN mkdir -p /var/run/clamav /var/lib/clamav /var/log/clamav \
    && chown -R clamav:clamav /var/run/clamav /var/lib/clamav /var/log/clamav \
    && sed -i 's/^Foreground .*$/Foreground true/g' /etc/clamav/clamd.conf \
    && sed -i 's/^Foreground .*$/Foreground true/g' /etc/clamav/freshclam.conf \
    && echo "TCPSocket 3310" >> /etc/clamav/clamd.conf \
    && echo "TCPAddr 127.0.0.1" >> /etc/clamav/clamd.conf

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY app/ ./app/
COPY test_config.py ./

# Copy startup script
COPY start.sh /app/start.sh

# Create necessary directories and set permissions
RUN mkdir -p /app/logs /app/temp \
    && chown -R bonifatus:bonifatus /app \
    && chmod -R 755 /app \
    && chmod +x test_config.py \
    && chmod +x /app/start.sh

# Health check
HEALTHCHECK --interval=30s --timeout=30s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8080/health || exit 1

# Expose port 8080 for Cloud Run
EXPOSE 8080

# Use startup script that runs ClamAV and the app
CMD ["/app/start.sh"]