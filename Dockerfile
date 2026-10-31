# RetentionIQ Production Dockerfile
FROM python:3.12-slim

# Prevent Python from writing .pyc files and buffer stdout/stderr
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PORT=5000

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application files
COPY . .

# Ensure data directory exists and set permissions
RUN mkdir -p /app/data && chmod -R 777 /app/data

# Run as non-root user
RUN useradd -m -u 1000 appuser && chown -R appuser:appuser /app
USER appuser

# Declare persistent volume for SQLite database storage
VOLUME ["/app/data"]

EXPOSE 5000

# Health check using curl against the dashboard
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:5000/ || exit 1

# Production WSGI startup via Gunicorn
CMD ["gunicorn", "--workers=4", "--bind=0.0.0.0:5000", "--timeout=120", "--access-logfile=-", "--error-logfile=-", "app.app:create_app()"]
