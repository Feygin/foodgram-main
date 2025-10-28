# Python base (slim is light but needs a few libs for psycopg2/Pillow)
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

# OS deps for psycopg2, Pillow (jpeg/zlib), and builds
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential gcc \
    libpq-dev \
    libjpeg-dev zlib1g-dev \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy and install deps first for better caching
COPY requirements.txt .
RUN pip install --upgrade pip && pip install -r requirements.txt

# Copy project
COPY . .

# Ensure a data directory exists and copy ingredients
RUN mkdir -p /app/data
COPY ./data/ingredients.json /app/data/ingredients.json

# Expose gunicorn port
EXPOSE 8000

CMD gunicorn foodgram.wsgi:application --bind 0.0.0.0:8000 --workers 3