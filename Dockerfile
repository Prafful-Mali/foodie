# FROM python:3.12-slim

# ENV PYTHONDONTWRITEBYTECODE=1
# ENV PYTHONUNBUFFERED=1

# WORKDIR /app

# RUN apt-get update && apt-get install -y \
#     build-essential \
#     libpq-dev \
#     curl \
#     && rm -rf /var/lib/apt/lists/*

# RUN curl -LsSf https://astral.sh/uv/install.sh | sh
# ENV PATH="/root/.local/bin:$PATH"

# COPY pyproject.toml uv.lock ./

# RUN uv sync --frozen --no-dev

# COPY . .

# RUN mkdir -p logs

# EXPOSE 8000

# CMD ["uv", "run", "python", "manage.py", "runserver", "0.0.0.0:8000"]


# ====================================
# Stage 1: Builder - Install dependencies
# ====================================
FROM python:3.12-slim AS builder

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /build

# Install build dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    libpq-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install uv
RUN curl -LsSf https://astral.sh/uv/install.sh | sh
ENV PATH="/root/.local/bin:$PATH"

# Copy dependency files
COPY pyproject.toml uv.lock ./

# Create virtual environment and install dependencies using uv
# uv will handle creating the venv with all necessary tools
RUN uv sync --frozen

# The venv is created at .venv by default, let's move it to /opt/venv
RUN mv .venv /opt/venv

# Verify the installation worked
RUN /opt/venv/bin/python -c "import django; print(f'✓ Django {django.__version__} installed successfully')" && \
    /opt/venv/bin/celery --version | head -n 1

# ====================================
# Stage 2: Runtime - Lean production image
# ====================================
FROM python:3.12-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
# Critical: Set PATH to include venv
ENV PATH="/opt/venv/bin:$PATH"
ENV VIRTUAL_ENV="/opt/venv"

WORKDIR /app

# Install ONLY runtime dependencies (no build tools!)
RUN apt-get update && apt-get install -y \
    libpq5 \
    && rm -rf /var/lib/apt/lists/*

# Copy the entire virtual environment from builder stage
COPY --from=builder /opt/venv /opt/venv

# Verify venv was copied correctly
RUN python --version && \
    python -c "import django; print(f'✓ Django {django.__version__} ready')" && \
    which celery && \
    celery --version | head -n 1

# Copy application code
COPY . .

# Create necessary directories
RUN mkdir -p logs media static

EXPOSE 8000

# Default command
CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]