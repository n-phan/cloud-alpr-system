FROM python:3.11-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Install system dependencies for OpenCV
# libgl1: Required for OpenGL operations
# libglib2.0-0: Required for event loop handling in cv2
RUN apt-get update && apt-get install -y --no-install-recommends \
    libgl1 \
    libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

# Set the working directory
WORKDIR /app

# Ensure directories are treated as modules
RUN mkdir -p /app/ml /app/preprocessing /app/s3 /app/sqs /app/worker

# Install Python requirements
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the project files
COPY . .

# Explicitly add __init__.py files if they are missing
RUN touch /app/ml/__init__.py /app/preprocessing/__init__.py /app/sqs/__init__.py /app/worker/__init__.py

# Run the worker
CMD ["python", "main.py"]