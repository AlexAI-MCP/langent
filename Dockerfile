FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY pyproject.toml README.md ./
COPY langent/ langent/
RUN pip install --no-cache-dir -e .

# Copy config and visualizer
COPY config/ config/
COPY langent/visualizer/ langent/visualizer/

# Create data directory
RUN mkdir -p /app/data

EXPOSE 8000

ENV LANGENT_WORKSPACE=/app/workspace
ENV CHROMA_DB_PATH=/app/data/chroma_db

CMD ["langent", "serve", "--host", "0.0.0.0", "--port", "8000"]
