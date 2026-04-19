FROM python:3.10-slim

WORKDIR /app

# =========================
# ENV
# =========================
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

# =========================
# SYSTEM DEPENDENCIES
# =========================
RUN apt-get update && apt-get install -y --no-install-recommends \
    libgl1 \
    libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

# =========================
# PYTHON DEPENDENCIES
# =========================
RUN pip install --upgrade pip

# CPU TORCH (IMPORTANT FOR ECS COST)
RUN pip install torch torchvision --index-url https://download.pytorch.org/whl/cpu

COPY requirements.txt .
RUN pip install -r requirements.txt

# =========================
# APP FILES
# =========================
COPY main.py .
COPY best.pt .

# =========================
# RUN
# =========================
CMD ["python", "main.py"]