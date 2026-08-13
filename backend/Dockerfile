FROM python:3.11-slim

WORKDIR /app

# System deps for building some Python packages (chromadb/sentence-transformers deps)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app ./app

# Persisted data lives under /app (chroma_data mounted via compose volume,
# app/data holds the small JSON registry)
RUN mkdir -p /app/app/data /app/chroma_data

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
