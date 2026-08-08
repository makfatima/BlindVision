# Build from the poc/ directory: `docker build -f server/Dockerfile -t blindvision-poc .`
FROM python:3.11-slim

WORKDIR /app

# libgl1 / libglib2.0-0 are common runtime deps for opencv/ultralytics image codecs
RUN apt-get update && apt-get install -y --no-install-recommends \
    libgl1 libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY server/ .

EXPOSE 8000
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8000"]
