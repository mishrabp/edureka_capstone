# Base Image
FROM python:3.10-slim

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    HF_HOME=/home/user/.cache \
    HOME=/home/user

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Create a non-root user and ensure home directory exists
RUN useradd -m -u 1000 user && \
    mkdir -p /home/user/.cache && \
    chown -R user:user /home/user

# Copy project files and set ownership
COPY --chown=user:user . .

# Ensure scripts are executable
RUN chmod +x scripts/*.sh

# Switch to non-root user
USER user
ENV PATH=/home/user/.local/bin:$PATH

# Install Python dependencies
RUN pip install -e ".[dev]"

# Expose ports (HF defaults to 7860)
EXPOSE 7860
EXPOSE 8001

# Start the application via script
ENTRYPOINT ["/bin/bash", "scripts/hf_start.sh"]
