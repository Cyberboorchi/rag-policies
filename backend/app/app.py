# backend/app/app.py
import os, uuid
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from qdrant_client import QdrantClient
from qdrant_client.models import PointStruct
import google.generativeai as genai
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# =========================
# Config
# =========================
QDRANT_URL = os.getenv("QDRANT_URL")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
COLLECTION_NAME = "policies"

# Models (Gemini-г ашиглана)
EMBED_MODEL_GEMINI = "models/text-embedding-004"
CHAT_MODEL_GEMINI = "models/gemini-1.5-flash"

# =========================
# App & CORS
# =========================
app = FastAPI(title="RAG API (Gemini embeddings + Qdrant + Gemini)")
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

# ===========================
# Embedding function (Gemini-г ашиглана)
# ===========================
def get_embedding(text: str):
    """Gemini API-гаар embedding үүсгэнэ."""
    if not GEMINI_API_KEY:
        raise HTTPException(status_code=500, detail="Gemini API түлхүүр тохируулагдаагүй байна.")
    
    try:
        genai.configure(api_key=GEMINI_API_KEY)
        response = genai.embed_content(
            model=EMBED_MODEL_GEMINI,
            content=text,
            task_type="retrieval_document"
        )
        return response['embedding']
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Embedding үүсгэхэд алдаа гарлаа: {e}")

# ===========================
# Retrieval function
# ===========================
def retrieve_docs(question: str, top_k=5):
    """Qdrant-аас холбогдох баримтыг хайна."""
    results = []
    try:
        vector = get_embedding(question)
        qdrant_hits = qc.search(
            collection_name=COLLECTION_NAME,
            query_vector=vector,
            limit=top_k,
            with_payload=True
        )

        # Qdrant-ийн хайлтын үр дүнг оноогоор нь буурахаар эрэмбэлэх
        sorted_hits = sorted(qdrant_hits, key=lambda hit: hit.score, reverse=True)

        for hit in sorted_hits:
            # Хариултын оноо 0.8-аас багагүй байх эсвэл хамааралгүй байвал хасах
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


# ===========================
# Generation function (Gemini-г ашиглана)
# ===========================
def generate_answer_gemini(question: str, docs: list):
    """Gemini API-г ашиглан хариулт үүсгэнэ."""
    if not docs:
        return "Олдсон мэдээлэл байхгүй тул хариулт өгөх боломжгүй."
    
    context_text = "\n".join([f"- {d.get('text', '')}" for d in docs])
    prompt = f"""Өгөгдсөн мэдээлэлд үндэслэн асуултад Монгол хэлээр товч бөгөөд ойлгомжтой хариулт өгнө үү. Хэрэв мэдээлэлд хариулт байхгүй бол "Мэдээлэл дутмаг байна" гэж хариулна уу.

Мэдээлэл:
{context_text}

Асуулт:
{question}

Хариулт:
"""
    try:
        model = genai.GenerativeModel(CHAT_MODEL_GEMINI)
        response = model.generate_content(prompt)
        return response.text.strip()
    except Exception as e:
        print(f"Gemini API-г дуудахад алдаа гарлаа: {e}")
        return f"Gemini API-г дуудахад алдаа гарлаа: {e}"

# ===========================
# API Endpoints
# ===========================
@app.post("/add_doc")
def add_doc(doc: Document):
    """Баримт + metadata-г embedding болгоод Qdrant-д хадгална."""
    try:
        vec = get_embedding(doc.text)
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
    """Асуултад хариулт өгөх үндсэн endpoint (Gemini-г ашиглана)."""
    try:
        docs = retrieve_docs(query.question)
        gemini_answer = generate_answer_gemini(query.question, docs)
        return {
            "question": query.question,
            "retrieved_docs": docs,
            "gemini_answer": gemini_answer
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))