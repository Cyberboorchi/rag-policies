import requests

OLLAMA_URL = "http://ollama:11434"  # контейнер доторх URL
model = "mistral"  # эсвэл өөр загвар
texts = ["Hello world"]

payload = {
    "model": model,
    "input": texts
}

try:
    response = requests.post(f"{OLLAMA_URL}/api/embeddings", json=payload)
    print("Status code:", response.status_code)
    print("Response JSON:", response.json())
except Exception as e:
    print("Ollama connection failed:", e)
