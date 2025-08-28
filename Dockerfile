# PebbleMind Dockerfile
# Multi-stage build for optimal image size

# Build stage
FROM python:3.11-slim as builder

# Install system dependencies for llama.cpp and BLAS
RUN apt-get update && apt-get install -y \
    build-essential \
    cmake \
    libopenblas-dev \
    libomp-dev \
    llvm \
    clang \
    git \
    && rm -rf /var/lib/apt/lists/*

# Set environment variables for BLAS optimization
ENV OMP_NUM_THREADS=4
ENV OPENBLAS_NUM_THREADS=4
ENV CMAKE_ARGS="-DGGML_BLAS=ON -DGGML_BLAS_VENDOR=OpenBLAS -DCMAKE_BUILD_TYPE=Release -DGGML_NATIVE=ON"

# Create virtual environment
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Install Python dependencies
COPY pyproject.toml .
RUN pip install --upgrade pip && \
    pip install -e . && \
    pip install llama-cpp-python --force-reinstall --no-cache-dir

# Runtime stage
FROM python:3.11-slim as runtime

# Install runtime dependencies
RUN apt-get update && apt-get install -y \
    libopenblas0 \
    libomp5 \
    libgomp1 \
    && rm -rf /var/lib/apt/lists/*

# Copy virtual environment from builder
COPY --from=builder /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Create non-root user
RUN useradd --create-home --shell /bin/bash pebblemind
USER pebblemind

# Create directories
RUN mkdir -p /app/data /app/cache /app/models

# Set working directory
WORKDIR /app

# Copy application code
COPY --chown=pebblemind:pebblemind . .

# Set environment variables
ENV PYTHONPATH=/app
ENV OMP_NUM_THREADS=4
ENV OPENBLAS_NUM_THREADS=4

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=30s --retries=3 \
    CMD python -c "from pebblemind.core import PebbleMind; print('OK')" || exit 1

# Default command
CMD ["pebblemind", "serve", "--host", "0.0.0.0"]
