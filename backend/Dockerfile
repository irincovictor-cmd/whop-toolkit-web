# Whop Toolkit backend microservice
# Deploy target: Render or Railway (any container host works)

FROM python:3.11-slim

# ffmpeg + yt-dlp's runtime needs (git for pip installs of yt-dlp master if ever needed)
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app/ ./app/

# Render/Railway both set $PORT -- respect it instead of hardcoding 8000
ENV PORT=8000
EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s \
    CMD curl -f http://localhost:${PORT}/health || exit 1

CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT}"]
