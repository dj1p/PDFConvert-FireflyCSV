FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application
COPY converter.py .
COPY api_server.py .

# Create directories for uploads and outputs
RUN mkdir -p /app/uploads /app/outputs

# Expose port for API
EXPOSE 8000

# Run the API server
CMD ["python", "api_server.py"]
