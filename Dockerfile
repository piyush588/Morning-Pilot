FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application and frontend code
COPY app/ app/
COPY frontend/ frontend/
COPY scripts/ scripts/
COPY README.md .

# Create runtime directories and seed initial demo profile
RUN mkdir -p app/data/briefings app/data/profiles app/data/cache && \
    python scripts/seed_profile.py

ENV APP_HOST=0.0.0.0
ENV APP_PORT=8001
EXPOSE 8001

CMD ["python", "-m", "app.main"]
