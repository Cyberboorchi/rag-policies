FROM python:3.11-slim

# системийн хэрэгцээтэй пакетууд
RUN apt-get update && apt-get install -y curl unzip

# Ollama CLI татаж суулгах
RUN curl -L https://ollama.com/download/ollama-linux -o /usr/local/bin/ollama && \
    chmod +x /usr/local/bin/ollama

WORKDIR /app
COPY . /app

# Copy requirements first
COPY requirements.txt .

# Upgrade pip first (hash алдаа шийдэх)
RUN python -m pip install --upgrade pip

# Install dependencies (sentence-transformers болон бусад)
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Expose FastAPI port
EXPOSE 8000

# Start FastAPI
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8000"]
