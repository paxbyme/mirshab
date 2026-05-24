# syntax=docker/dockerfile:1
FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# Tizim bog'liqliklari (asyncpg build, OCR ixtiyoriy)
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt requirements-ml.txt ./
RUN pip install --upgrade pip && pip install -r requirements.txt

# Opsional og'ir ML paketlar (NudeNet + OCR). Yoqish uchun:
#   docker build --build-arg INSTALL_ML=true .
# Railway'da: service Settings > Build > build arg INSTALL_ML=true qo'ying.
ARG INSTALL_ML=false
RUN if [ "$INSTALL_ML" = "true" ]; then \
        apt-get update && apt-get install -y --no-install-recommends tesseract-ocr \
        && rm -rf /var/lib/apt/lists/* \
        && pip install -r requirements-ml.txt ; \
    fi

COPY . .

# Loglar uchun papka
RUN mkdir -p logs

# Botni ishga tushirish
CMD ["python", "-m", "bot.main"]
