FROM python:3.12-slim

# tesseract-ocr = the actual OCR engine binary (pytesseract is just a wrapper around it)
# libglib2.0-0 = required by opencv-python-headless at import time on slim images
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        tesseract-ocr \
        libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Render injects $PORT at runtime; app.py already reads it via os.environ.
CMD ["python", "app.py"]
