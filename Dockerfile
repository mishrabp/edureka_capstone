# Base Image
FROM python:3.10-slim

# Set working directory
WORKDIR /app

# Install system dependencies (build-essential for some pip packages)
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    software-properties-common \
    && rm -rf /var/lib/apt/lists/*

# Copy project files
COPY . .

# Install Python dependencies
RUN pip install --no-cache-dir -e ".[dev]"

# Create a non-root user (good practice for HF Spaces)
RUN useradd -m -u 1000 user
USER user
ENV HOME=/home/user \
    PATH=/home/user/.local/bin:$PATH

# Expose Streamlit port (HF defaults to 7860)
EXPOSE 7860

# Expose FastAPI port (internal)
EXPOSE 8001

# Start the application via script
ENTRYPOINT ["/bin/bash", "scripts/hf_start.sh"]
