FROM python:3.11-slim-bookworm

# Install ffmpeg, rclone, curl, and SSL certificates
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    rclone \
    curl \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Create non-root system group and user (UID/GID 1000)
RUN groupadd -g 1000 blaine && \
    useradd -u 1000 -g blaine -m -s /bin/bash blaine

WORKDIR /app

# Copy dependency manifest and install Python libraries
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application source code
COPY src/ ./src/
COPY README.md .

# Create persistent storage directories and assign ownership to blaine
RUN mkdir -p /var/blaine/scratch /var/blaine/organized /home/blaine/.config/rclone && \
    chown -R blaine:blaine /app /var/blaine /home/blaine

# Run process as non-root user
USER blaine

ENV PYTHONUNBUFFERED=1

CMD ["python3", "-m", "src.main", "bot"]
