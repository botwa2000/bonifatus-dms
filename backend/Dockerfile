# backend/Dockerfile
FROM python:3.11-slim

LABEL maintainer="bonifatus.app@gmail.com"
LABEL description="Bonifatus DMS - Production Document Management System"
LABEL version="1.0.0"

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONPATH="/app"

WORKDIR /app

# Create non-root user for security
RUN groupadd -r bonifatus && useradd -r -g bonifatus bonifatus

# Install system dependencies
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        gcc \
        libc6-dev \
        curl \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY app/ ./app/

# Create necessary directories and set permissions
RUN mkdir -p /app/logs /app/temp \
    && chown -R bonifatus:bonifatus /app \
    && chmod -R 755 /app

# Switch to non-root user
USER bonifatus

# Health check
HEALTHCHECK --interval=30s --timeout=30s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8080/health || exit 1

# Expose port 8080 for Cloud Run
EXPOSE 8080

# Run application using main.py which properly handles PORT
CMD ["python", "-m", "app.main"]