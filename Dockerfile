FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    curl \
    git \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# Copy requirements
COPY requirements-prod.txt requirements.txt .

# Install Python dependencies
# Install CPU-only torch first, then other dependencies
RUN pip install --no-cache-dir --index-url https://download.pytorch.org/whl/cpu torch==2.1.2 && \
    pip install --no-cache-dir transformers==4.36.2 huggingface-hub==0.20.3 sentence-transformers==2.3.1 && \
    pip install --no-cache-dir -r requirements-prod.txt && \
    pip cache purge || true

# Copy application code
COPY . .

# Expose API port
EXPOSE 8000

# Run API server
CMD ["uvicorn", "api.app:app", "--host", "0.0.0.0", "--port", "8000"]

