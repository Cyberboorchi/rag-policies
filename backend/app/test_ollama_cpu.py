# test_ollama_cpu.py
import requests
import json

# Ollama серверийн контейнер доторх URL
OLLAMA_URL = "http://ollama:11434"
MODEL = "mistral"  # эсвэл өөр загвар
TEXTS = ["Hello world"]

def test_embedding():
    payload = {
        "model": MODEL,
        "input": TEXTS, 
        "batch_size": 1  # CPU горимд batch_size-ийг 1 болгох
    }

    try:
        response = requests.post(f"{OLLAMA_URL}/api/embeddings", json=payload, timeout=30)
        print("Status code:", response.status_code)
        resp_json = response.json()
        print("Response JSON:", json.dumps(resp_json, indent=2))

        if "embedding" in resp_json and resp_json["embedding"]:
            print("✅ Embedding received successfully!")
        else:
            print("⚠️ Embedding is empty. Ollama model might be loading or CPU-only mode limitation.")

    except requests.exceptions.RequestException as e:
        print("❌ Request failed:", e)

if __name__ == "__main__":
    test_embedding()
