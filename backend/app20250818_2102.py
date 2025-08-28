# app.py
from fastapi import FastAPI
from pydantic import BaseModel
from qdrant_client import QdrantClient
from qdrant_client.http.models import Filter
from qdrant_client.models import PointStruct   # ← энэ мөрийг нэмэх хэрэгтэй
import os, requests
import uuid

# ===========================
# Config
# ===========================
QDRANT_URL = os.getenv("QDRANT_URL", "http://localhost:6333")
OLLAMA_URL = os.getenv("OLLAMA_URL", "http://ollama:11434")
COLLECTION_NAME = "policies"

# ===========================
# FastAPI app & Qdrant client
# ===========================
app = FastAPI()
qc = QdrantClient(url=QDRANT_URL)

# ===========================
# Pydantic model
# ===========================
class Query(BaseModel):
    question: str
    

class Document(BaseModel):
    text: str

# ===========================
# Embedding function
# ===========================
def get_embedding(text: str):
    url = f"{OLLAMA_URL}/v1/embeddings"
    payload = {
        "model": "nomic-embed-text:latest",
        "input": text
    }
    response = requests.post(url, json=payload)
    if not response.ok:
        raise ValueError(f"Embedding API request failed: {response.status_code} {response.text}")
    
    data = response.json()
    if "data" not in data or len(data["data"]) == 0 or "embedding" not in data["data"][0]:
        raise ValueError(f"Embedding API did not return embedding. Response: {data}")
    
    return data["data"][0]["embedding"]


# ===========================
# Insert document
# ===========================
def insert_doc(doc: Document):
    embedding = get_embedding(doc.text)
    point_id = str(uuid.uuid4())

    qc.upsert(
        collection_name=COLLECTION_NAME,
        points=[
            PointStruct(
                id=point_id,
                vector=embedding,
                payload={"text": doc.text}
            )
        ]
    )
    return point_id


@app.post("/add_doc")
def add_doc(doc: Document):
    doc_id = insert_doc(doc)
    return {
        "status": "success",
        "id": doc_id,
        "text": doc.text
    }


# ===========================
# Retrieve docs from Qdrant
# ===========================
def retrieve_docs(question: str, top_k: int = 5):
    vector = get_embedding(question)
    
    result = qc.search(
        collection_name=COLLECTION_NAME,
        query_vector=vector,
        limit=top_k,
        with_payload=True
    )
    
    hits = []
    for hit in result:
        hits.append({
            "id": hit.id,
            "score": hit.score,
            "payload": hit.payload
        })
    return hits

# ===========================
# /ask endpoint
# ===========================
@app.post("/ask")
def ask(query: Query):
    docs = retrieve_docs(query.question)

    # JSON format
    json_result = {
        "question": query.question,
        "answers": docs
    }

    # Human-readable text
    text_result = f"Асуулт: {query.question}\n\nХариултууд:\n"
    for i, d in enumerate(docs, start=1):
        text_result += f"{i}. {d['payload'].get('text','')}\n"

    return {
        "json": json_result,
        "text": text_result
    }
