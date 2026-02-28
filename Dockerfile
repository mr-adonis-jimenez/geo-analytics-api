# Multi-stage Dockerfile for Geo-Analytics API
# Optimized for production deployment with minimal image size

# Stage 1: Builder
FROM python:3.14-slim as builder

WORKDIR /app

# Install build dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir --user -r requirements.txt

# Stage 2: Runtime
FROM python:3.14-slim

WORKDIR /app

# Create non-root user for security
RUN useradd -m -u 1000 geoanalytics && \
    chown -R geoanalytics:geoanalytics /app

# Copy Python dependencies from builder
COPY --from=builder /root/.local /home/geoanalytics/.local

# Copy application code
COPY --chown=geoanalytics:geoanalytics . .

# Set PATH to include user-installed packages
ENV PATH=/home/geoanalytics/.local/bin:$PATH

# Switch to non-root user
USER geoanalytics

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health').read()" || exit 1

# Run the application
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
