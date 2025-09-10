# backend/app/app.py
import os, uuid
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from qdrant_client import QdrantClient
from qdrant_client.models import PointStruct
import requests
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# =========================
# Config
# =========================
QDRANT_URL = os.getenv("QDRANT_URL")
OLLAMA_URL = os.getenv("OLLAMA_URL")

COLLECTION_NAME = os.getenv("COLLECTION_NAME")

EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL")
CHAT_MODEL = os.getenv("CHAT_MODEL")

# =========================
# App & CORS
# =========================
app = FastAPI(title="RAG API (FastAPI + Qdrant + Ollama)")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
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
    metadata: dict | None = None


def get_query_embedding_ollama(text: str):
    payload = {
        "model": EMBEDDING_MODEL,
        "prompt": text
    }
    response = requests.post(f"{OLLAMA_URL}/api/embeddings", json=payload)
    if response.status_code != 200:
        raise Exception(f"Ollama embedding error: {response.text}")
    data = response.json()
    return data["embedding"]

  

# ===========================
# Retrieval function
# ===========================
def retrieve_docs(question: str, top_k=3):
    """Qdrant-аас холбогдох баримтыг хайна."""
    results = []
    try:
        # vector = get_query_embedding(question)
        vector = get_query_embedding_ollama(question)
        qdrant_hits = qc.search(
            collection_name=COLLECTION_NAME,
            query_vector=vector,
            limit=top_k,
            with_payload=True
        )

        # Qdrant-ийн хайлтын үр дүнг оноогоор нь буурахаар эрэмбэлэх
        sorted_hits = sorted(qdrant_hits, key=lambda hit: hit.score, reverse=True)

        for hit in sorted_hits:
            # Хариултын оноо 0.5-аас багагүй байх эсвэл хамааралгүй байвал хасах
            if hit.score > 0.8:
                payload = hit.payload or {}
                results.append({
                    "source": "qdrant",
                    "id": hit.id,
                    "score": hit.score,
                    "text": payload.get("text", ""),
                    "metadata": {k: v for k, v in payload.items() if k != "text"}
                })
            else:
                # Хэрэв оноо бага бол цааш үргэлжлүүлэхгүй
                continue

    except Exception as e:
        print(f"Qdrant хайлтад алдаа гарлаа: {e}")
    return results

def query_ollama(prompt, model=CHAT_MODEL):
    payload = {"model": model, "prompt": prompt, "stream": False}
    resp = requests.post(f"{OLLAMA_URL}/api/generate", json=payload)
    if resp.status_code != 200:
        raise Exception(f"Ollama generate error: {resp.text}")
    return resp.json().get("response", "").strip()

def generate_answer_ollama(question, docs):
    """Ollama-г ашиглан хариулт үүсгэнэ."""
    if not docs:
        return "Олдсон мэдээлэл байхгүй тул хариулт өгөх боломжгүй."
    
    context_text = "\n".join([f"- {d.get('text', '')}" for d in docs])

    # Монгол хэл дээр гарахыг зааварласан prompt
    prompt = f"""
Асуулт болон өгөгдсөн мэдээлэлд үндэслэн зөвхөн Монгол хэлээр товч бөгөөд ойлгомжтой хариулт өгнө үү. 
Хэрэв мэдээлэлд хариулт байхгүй бол "Мэдээлэл дутмаг байна" гэж хариул.

Мэдээлэл:
{context_text}

Асуулт:
{question}

Хариулт (Монгол хэлээр):
"""
    print("prompt : ", prompt)
    return query_ollama(prompt)



# ===========================
# API Endpoints
# ===========================
@app.post("/add_doc")
def add_doc(doc: Document):
    """Баримт + metadata-г embedding болгоод Qdrant-д хадгална."""
    try:
        # vec = get_document_embedding(doc.text)
        vec = get_query_embedding_ollama(doc.text)
        pid = str(uuid.uuid4())
        payload = {"text": doc.text}
        if doc.metadata:
            payload.update(doc.metadata)
        qc.upsert(
            collection_name=COLLECTION_NAME,
            points=[PointStruct(id=pid, vector=vec, payload=payload)],
        )
        return {"status": "success", "id": pid, "payload": payload}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/ask")
def ask(query: Query):
    
    try:
        docs = retrieve_docs(query.question)
        ollama_answer = generate_answer_ollama(query.question, docs)
        return {
            "question": query.question,
            "retrieved_docs": docs,
            "ollama_answer": ollama_answer
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
