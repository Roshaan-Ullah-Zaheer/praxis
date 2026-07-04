FROM python:3.11-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1

# System deps: Tesseract for OCR of scanned pages, poppler for PDF rendering.
RUN apt-get update \
    && apt-get install -y --no-install-recommends tesseract-ocr poppler-utils \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .

# Hugging Face Spaces runs the container as a non-root user, so the app directory
# isn't writable. Keep the local store (SQLite + uploads) in a writable path.
ENV LOCAL_DATA_DIR=/tmp/praxis-data

EXPOSE 7860

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "7860"]
