# Base Image
FROM python:3.10-slim

# Copy uv binary from the official image
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

# Set working directory
WORKDIR /app

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    UV_COMPILE_BYTECODE=1 \
    UV_SYSTEM_PYTHON=1 \
    HOME=/home/user \
    ANONYMIZED_TELEMETRY=False \
    CHROMA_SERVER_NOFILE=65536

# Copy project files
COPY . .

# Install Python dependencies using uv (as root, into system site-packages)
# --no-binary :none: forces pre-built wheels only — no compilation
RUN uv pip install --no-cache .

# Create a non-root user and fix permissions
RUN useradd -m -u 1000 user && \
    mkdir -p /home/user/.cache && \
    chown -R user:user /home/user && \
    chown -R user:user /app

# Ensure scripts are executable
RUN chmod +x scripts/*.sh

# Switch to non-root user
USER user
ENV PATH=/home/user/.local/bin:$PATH

# Expose ports (HF defaults to 7860)
EXPOSE 7860
EXPOSE 8001

# Start the application via script
ENTRYPOINT ["/bin/bash", "scripts/hf_start.sh"]
