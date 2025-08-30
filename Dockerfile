FROM python:3.12-slim

# Disable interactive prompts
ENV DEBIAN_FRONTEND=noninteractive

# Set project root in PYTHONPATH (important for Celery & FastAPI imports)
ENV PYTHONPATH=/app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    libpq-dev \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy code
COPY . /app

# Upgrade pip
RUN pip install --upgrade pip

# Install dependencies (optimized for CPU)
RUN pip install --no-cache-dir --extra-index-url https://download.pytorch.org/whl/cpu -r requirements.txt

# Expose FastAPI port
EXPOSE 8000

# 👇 This is the only real change
CMD ["gunicorn", "-w", "1", "-k", "uvicorn.workers.UvicornWorker", "app.main:app", "--bind", "0.0.0.0:8000"]
