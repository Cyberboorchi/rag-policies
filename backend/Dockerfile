FROM python:3.11-slim

WORKDIR /app

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
