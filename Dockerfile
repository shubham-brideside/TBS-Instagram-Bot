# Production-ready Dockerfile for Instagram Bot
FROM python:3.12-slim

# Set environment variables for production
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    ENVIRONMENT=production \
    FLASK_APP=main.py \
    FLASK_ENV=production \
    PORT=8000

# Set work directory
WORKDIR /app

# Install system dependencies required for MySQL and other packages
RUN apt-get update && apt-get install -y \
    gcc \
    default-libmysqlclient-dev \
    pkg-config \
    curl \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# Copy requirements first to leverage Docker cache layers
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create non-root user for security
RUN groupadd -r appgroup && useradd -r -g appgroup appuser && \
    chown -R appuser:appgroup /app && \
    chmod -R 755 /app

# Switch to non-root user
USER appuser

# Expose port
EXPOSE 5000


# Use Gunicorn for production server
CMD ["gunicorn", "--bind", "0.0.0.0:5000", "--workers", "10", "--worker-class", "sync", "--timeout", "120", "--keep-alive", "5", "--max-requests", "1000", "--max-requests-jitter", "100", "--preload", "--log-level", "info", "--access-logfile", "-", "--error-logfile", "-", "main:app"] 