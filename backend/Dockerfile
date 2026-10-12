FROM python:3.12-slim

WORKDIR /app

# Install system dependencies needed for compiling packages if any
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy and install python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy source folders
COPY backend/ /app/backend/
COPY database/ /app/database/
COPY data/ /app/data/
COPY outputs/ /app/outputs/

# Set Python Path to workspace root
ENV PYTHONPATH=/app
ENV TESTING=False

EXPOSE 8000

# Start backend using production command without --reload
CMD ["uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8000"]
