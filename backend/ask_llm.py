import requests
import argparse

# Configuration
OLLAMA_URL = "http://ollama:11434"
MODEL_NAME = "steamdj/mistral-cpu-only"
# MODEL_NAME = "nomic-embed-text"


def ask_question(question: str):
    response = requests.post(f"{OLLAMA_URL}/api/generate", json={
        "model": MODEL_NAME,
        "prompt": question,
        "stream": False
    })

    if response.status_code == 200:
        answer = response.json().get("response", "")
        print(f"\n🧠 Хариулт:\n{answer}")
    else:
        print(f"❌ Алдаа гарлаа: {response.status_code}\n{response.text}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="LLM-д асуулт асуух CLI")
    parser.add_argument("question", type=str, help="Асуух асуулт")
    args = parser.parse_args()

    ask_question(args.question)
