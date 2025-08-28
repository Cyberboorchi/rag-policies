# app.py
import os
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from qdrant_client import QdrantClient
from qdrant_client.models import Filter, FieldCondition, MatchValue

import requests

# Config
QDRANT_URL = os.getenv("QDRANT_URL", "http://localhost:6333")
OLLAMA_URL = os.getenv("OLLAMA_URL", "http://ollama:11434")
COLLECTION_NAME = "policies"
EMBEDDING_DIM = 768  # Тохируулах

# Init
app = FastAPI()
qc = QdrantClient(url=QDRANT_URL)

# Pydantic models
class Query(BaseModel):
    question: str

# Ollama embedding function
def get_embedding(text: str):
    if isinstance(text, list):
        raise HTTPException(status_code=400, detail="Text input must be a single string, not a list")
    if "\n" in text:
        text = text.replace("\n", " ")

    try:
        resp = requests.post(f"{OLLAMA_URL}/v1/embeddings", json={
            "model": "nomic-embed-text:latest",
            "input": text
        })
        resp.raise_for_status()
        data = resp.json()
        embedding = data.get("data", [{}])[0].get("embedding", [])
        if not embedding or len(embedding) != EMBEDDING_DIM:
            raise HTTPException(
                status_code=500,
                detail=f"Embedding API did not return valid embedding. Response: {data}"
            )
        return embedding
    except requests.exceptions.RequestException as e:
        raise HTTPException(status_code=500, detail=f"Embedding API request error: {e}")

# Retrieve documents from Qdrant
def retrieve_docs(question: str, top_k: int = 3):
    vector = get_embedding(question)

    try:
        results = qc.search(
            collection_name=COLLECTION_NAME,
            query_vector=vector,
            limit=top_k
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Qdrant query error: {e}")

    docs = []
    for r in results:
        docs.append({
            "id": r.id,
            "score": r.score,
            "payload": r.payload
        })
    return docs

# API endpoint
@app.post("/ask")
def ask(query: Query):
    docs = retrieve_docs(query.question)
    return {"question": query.question, "answers": docs}

# Healthcheck
@app.get("/")
def root():
    return {"status": "ok"}
