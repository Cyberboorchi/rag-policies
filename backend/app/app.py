# backend/app.py
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from qdrant_client import QdrantClient
from qdrant_client.models import PointStruct
import os, requests, uuid, json

# ===========================
# Config
# ===========================
QDRANT_URL = os.getenv("QDRANT_URL")
OLLAMA_URL = os.getenv("OLLAMA_URL")
COLLECTION_NAME = "policies"


# Models
EMBED_MODEL = "nomic-embed-text:latest"  # embedding model
CHAT_MODEL = "llama3:8b"            # updated chat/generation model

# ===========================
# FastAPI app & CORS
# ===========================
app = FastAPI()

# CORS: frontend origin-оос fetch зөвшөөрөх
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # эсвэл зөвхөн frontend URL-ийг: ["http://localhost:5500"]
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Qdrant client
qc = QdrantClient(url=QDRANT_URL)

# ===========================
# Pydantic models
# ===========================
class Query(BaseModel):
    question: str

class Document(BaseModel):
    text: str
    metadata: dict | None = None  # metadata: title, author, date, tags, etc.

# ===========================
# Embedding function
# ===========================
def get_embedding(text: str):
    url = f"{OLLAMA_URL}/v1/embeddings"
    payload = {"model": EMBED_MODEL, "input": text}
    try:
        response = requests.post(url, json=payload, timeout=30)
        response.raise_for_status()
        data = response.json()
        return data["data"][0]["embedding"]
    except requests.RequestException as e:
        raise ValueError(f"Embedding API failed: {e}")

# ===========================
# Insert document into Qdrant
# ===========================
def insert_doc(doc: Document):
    embedding = get_embedding(doc.text)
    point_id = str(uuid.uuid4())

    payload = {"text": doc.text}
    if doc.metadata:
        payload.update(doc.metadata)  # metadata fields added

    qc.upsert(
        collection_name=COLLECTION_NAME,
        points=[PointStruct(id=point_id, vector=embedding, payload=payload)]
    )
    return point_id

@app.post("/add_doc")
def add_doc(doc: Document):
    """
    Admin endpoint to insert documents with metadata into Qdrant
    """
    try:
        doc_id = insert_doc(doc)
        return {"status": "success", "id": doc_id, "payload": doc.dict()}
    except Exception as e:
        return {"status": "error", "message": str(e)}

# ===========================
# Multi-source retrieval
# ===========================
def retrieve_docs_multi(question: str, top_k=5):
    results = []

    # --- 1. Qdrant search ---
    try:
        vector = get_embedding(question)
        qdrant_hits = qc.search(
            collection_name=COLLECTION_NAME,
            query_vector=vector,
            limit=top_k,
            with_payload=True
        )
        for hit in qdrant_hits:
            results.append({
                "source": "qdrant",
                "id": hit.id,
                "score": hit.score,
                "text": hit.payload.get("text", "")
            })
    except Exception as e:
        print("Qdrant search failed:", e)

    # Sort by score descending
    results = sorted(results, key=lambda x: x.get("score", 0), reverse=True)
    return results[:top_k]

# ===========================
# Generate context-aware answer via Ollama chat model
# ===========================
def generate_answer(question: str, docs: list):
    if not docs:
        return "Олдсон мэдээлэл байхгүй тул хариулт өгөх боломжгүй."

    # Build context from retrieved docs
    context_text = "\n".join([f"- {d['text']}" for d in docs])
    print("Context for Ollama:", context_text)
    print("Question for Ollama:", question)
    
    prompt = f"""Дараах мэдээллээр Монгол хэлээр хариу бэлдэнэ үү:Мэдээлэл:{context_text} Асуулт: {question} Хариулт:"""

    print("Prompt for Ollama:", prompt)
    url = f"{OLLAMA_URL}/v1/completions"
    payload = {
        "model": CHAT_MODEL,
        "prompt": prompt
    }

    try:
        response = requests.post(url, json=payload)
        response.raise_for_status()
        data = response.json()
        print("Ollama response:", data)
        # answer = data.get("completion") or data.get("text") or ""
        answer = data.get("choices", [{}])[0].get("text", "")
        return answer.strip()
    except requests.RequestException as e:
        return f"Ollama completion API failed: {e}"

# ===========================
# /ask endpoint
# ===========================
@app.post("/ask")
def ask(query: Query):
    docs = retrieve_docs_multi(query.question)

    # JSON format
    json_result = {"question": query.question, "answers": docs}

    # Human-readable text
    text_result = f"Асуулт: {query.question}\n\nХариултууд (document source-ууд):\n"
    for i, d in enumerate(docs, start=1):
        text_result += f"{i}. [{d['source']}] {d['text']}\n"

    # Context-aware ChatGPT answer
    # chatgpt_answer = generate_answer(query.question, docs)

    return {
        "json": json_result
        # "text": text_result,
        # "chatgpt_answer": chatgpt_answer
    }
