# =============================================================================
# Dockerfile for Yupoo-to-ERP Sync Pipeline
# =============================================================================

# Use official Playwright Python image (pre-installed browsers and dependencies)
FROM mcr.microsoft.com/playwright/python:v1.40.0-jammy

# Set working directory
WORKDIR /app

# Copy requirements and install
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Install Chromium (specifically)
RUN playwright install chromium

# Copy project files
COPY . .

# Ensure logs and screenshots directories exist
RUN mkdir -p logs screenshots temp_images

# Environment variables (Can be overridden by .env or compose)
ENV PYTHONPATH=/app
ENV PYTHONUNBUFFERED=1

# Default command (will require ALBUM_ID as argument)
ENTRYPOINT ["python", "scripts/sync_pipeline.py"]
CMD ["--help"]
