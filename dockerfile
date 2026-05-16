FROM python:3.11-slim

WORKDIR /app

# Install git (needed for pip git dependencies like nflreadpy)
RUN apt-get update && apt-get install -y git && rm -rf /var/lib/apt/lists/*

# Install dependencies first (better caching)
COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

# Copy all project files
COPY . .

# Start the app
CMD ["uvicorn", "backend.server:app", "--host", "0.0.0.0", "--port", "10000"]
