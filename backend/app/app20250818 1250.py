# rag-policies/app/app.py

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from qdrant_client import QdrantClient
from qdrant_client.models import VectorParams, Distance
import requests
import os
import numpy as np

# Configuration
QDRANT_URL = os.getenv("QDRANT_URL", "http://qdrant:6333")
OLLAMA_URL = os.getenv("OLLAMA_URL", "http://ollama:11434")
COLLECTION_NAME = os.getenv("COLLECTION_NAME", "policies")
EMBEDDING_DIM = 768  # nomic-embed-text embedding size

# Initialize FastAPI app
app = FastAPI()

# Initialize Qdrant client
qc = QdrantClient(url=QDRANT_URL)

qc.recreate_collection(
    collection_name=COLLECTION_NAME,
    vectors_config=VectorParams(
        size=EMBEDDING_DIM,
        distance=Distance.COSINE
    )
)

# Request models
class Query(BaseModel):
    question: str

class Document(BaseModel):
    id: int
    text: str

# Embedding function
def get_embedding(text: str):
    try:
        resp = requests.post(f"{OLLAMA_URL}/api/embeddings", json={
            "model": "nomic-embed-text",
            "prompt": text
        })
        print(f"[Embedding] Status code: {resp.status_code}")
        print(f"[Embedding] Response body: {resp.text}")

        if resp.status_code != 200:
            raise HTTPException(status_code=500, detail=f"Embedding failed: {resp.text}")

        data = resp.json()
        embedding = data.get("embedding", [])

        if not embedding or len(embedding) != EMBEDDING_DIM:
            raise HTTPException(status_code=500, detail=f"Invalid embedding size: {len(embedding)}")

        print(f"[Embedding] Generated vector size: {len(embedding)}")
        return embedding

    except requests.exceptions.ConnectionError as ce:
        print(f"[Embedding] Connection error: {ce}")
        raise HTTPException(status_code=500, detail=f"Connection error: {str(ce)}")

    except requests.exceptions.RequestException as re:
        print(f"[Embedding] Request exception: {re}")
        raise HTTPException(status_code=500, detail=f"Request error: {str(re)}")

    except ValueError as ve:
        print(f"[Embedding] JSON decode error: {ve}")
        raise HTTPException(status_code=500, detail="Embedding API did not return valid JSON")

    except Exception as e:
        print(f"[Embedding] Unexpected error: {e}")
        raise HTTPException(status_code=500, detail=f"Unexpected error: {str(e)}")



# Retrieve documents
def retrieve_docs(query: str, top_k=3):
    embedding = get_embedding(query)
    hits = qc.search(
        collection_name=COLLECTION_NAME,
        query_vector=embedding,
        limit=top_k
    )
    return [hit.payload.get("text", "") for hit in hits if hit.payload.get("text")]

# Generate response using LLM   
def ask_gpt(context_docs: list, question: str, model_name: str = "mistral:instruct"):
    context_text = "\n\n".join(context_docs)
    prompt = f"Баримт бичгүүд:\n{context_text}\nАсуулт: {question}\nХариулт өгнө үү."

    # 1️⃣ Модел байгаа эсэхийг шалгах
    try:
        models_resp = requests.get(f"{OLLAMA_URL}/v1/models")
        models_resp.raise_for_status()
        models_json = models_resp.json()
        available_models = [m['id'] for m in models_json.get("data", [])]  # <-- data key
        if model_name not in available_models:
            raise HTTPException(
                status_code=400,
                detail=f"Model '{model_name}' олдсонгүй. Available models: {available_models}"
            )
    except requests.exceptions.RequestException as e:
        raise HTTPException(status_code=500, detail=f"Ollama серверт холбогдох боломжгүй: {e}")

    # 2️⃣ Generate хийх
    try:
        resp = requests.post(f"{OLLAMA_URL}/v1/completions", json={
            "model": model_name,
            "prompt": prompt,
            "max_tokens": 300
        })
        resp.raise_for_status()
        result = resp.json()
        return result["choices"][0]["text"]
    except requests.exceptions.RequestException as e:
        raise HTTPException(status_code=500, detail=f"LLM completion failed: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Unexpected error: {str(e)}")

    
# Ask endpoint
@app.post("/ask")
def ask(query: Query):
    print(f"[Ask] Question: {query.question}")
    docs = retrieve_docs(query.question)
    print(f"[Ask] Retrieved {len(docs)} documents.")

    if not docs:
        return {"answer": "No relevant information found."}

    answer = ask_gpt(docs, query.question)
    return {"answer": answer}

