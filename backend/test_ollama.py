# app/test_ollama_connection.py
import requests

def main():
    # Контейнер дотор Ollama руу холбогдох URL
    OLLAMA_URL = "http://ollama:11434"
    model = "mistral"  # эсвэл өөр загвар
    texts = ["Hello world from FastAPI container"]

    payload = {
        "model": model,
        "input": texts
    }

    try:
        response = requests.post(f"{OLLAMA_URL}/api/embeddings", json=payload, timeout=10)
        print("Status code:", response.status_code)
        print("Response JSON:", response.json())

        # Хэрэв embedding хоосон бол анхааруулга
        if not response.json().get("embedding"):
            print("⚠️ Ollama embedding empty")
        else:
            print("✅ Embedding received, length:", len(response.json()["embedding"]))

    except requests.exceptions.RequestException as e:
        print("❌ Failed to connect to Ollama:", e)

if __name__ == "__main__":
    main()
