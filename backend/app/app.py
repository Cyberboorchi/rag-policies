# backend/app.py
from __future__ import annotations
import os, uuid, json, logging, requests
from typing import Any, Dict, List, Optional

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from qdrant_client import QdrantClient
from qdrant_client.http import models as rest

from sentence_transformers import SentenceTransformer

# =========================
# Config
# =========================
QDRANT_URL = os.getenv("QDRANT_URL")
OLLAMA_URL = os.getenv("OLLAMA_URL")
COLLECTION_NAME = os.getenv("COLLECTION_NAME", "policies")

EMBED_MODEL_ID = os.getenv("EMBED_MODEL", "sentence-transformers/all-MiniLM-L6-v2")
EMBED_VECTOR_SIZE = 384  # all-MiniLM-L6-v2
EMBED_DISTANCE = "Cosine"

CHAT_MODEL = os.getenv("CHAT_MODEL", "llama3:8b")

# =========================
# App & CORS
# =========================
app = FastAPI(title="RAG API (HF embeddings + Qdrant + Ollama)")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # хэрэгтэй бол нарийсгаарай
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# =========================
# Clients & Models
# =========================
log = logging.getLogger("uvicorn")
qdrant = QdrantClient(url=QDRANT_URL)
embed_model = SentenceTransformer(EMBED_MODEL_ID)


def ensure_collection():
    """Qdrant-д collection байхгүй бол үүсгэнэ, тохиргоо таарахгүй байвал алдаа шиднэ."""
    cols = qdrant.get_collections().collections
    names = [c.name for c in cols]
    if COLLECTION_NAME not in names:
        qdrant.recreate_collection(
            collection_name=COLLECTION_NAME,
            vectors_config=rest.VectorParams(size=EMBED_VECTOR_SIZE, distance=EMBED_DISTANCE),
        )
        log.info(f"Created collection '{COLLECTION_NAME}' (size={EMBED_VECTOR_SIZE}, distance={EMBED_DISTANCE}).")
    else:
        schema = qdrant.get_collection(COLLECTION_NAME)
        print(schema)
        # Хэмжээг зөрчихгүйг түрхэн шалгана (нарийвчлалд vector_params төрөл л хангалттай)
        vs = schema.config.params.vectors
        print(vs)
        
        current_size = None
        if isinstance(vs, rest.VectorParams):
            current_size = vs.size
        elif isinstance(vs, rest.VectorParamsDiff):
            current_size = vs.size
        elif isinstance(vs, dict) and "size" in vs:
            current_size = vs["size"]
        if current_size and int(current_size) != EMBED_VECTOR_SIZE:
            raise RuntimeError(
                f"Collection '{COLLECTION_NAME}' vector size={current_size}, "
                f"but embed model requires {EMBED_VECTOR_SIZE}. "
                f"Please recreate the collection or change model."
            )


ensure_collection()

# =========================
# Schemas
# =========================
class Document(BaseModel):
    text: str = Field(..., description="Баримтын үндсэн текст")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Нэмэлт талбарууд: title, chapter, section, ...")

class Query(BaseModel):
    question: str
    top_k: int = Field(5, ge=1, le=20)

# =========================
# Helpers
# =========================
def embed(text: str) -> List[float]:
    try:
        return embed_model.encode(text).tolist()
    except Exception as e:
        raise RuntimeError(f"Embedding failed: {e}")

def trim_text(s: str, max_chars: int) -> str:
    if len(s) <= max_chars:
        return s
    return s[:max_chars] + " …"

def build_prompt(question: str, docs: List[Dict[str, Any]]) -> str:
    # Document бүрээс 1200 тэмдэгт хүртэл авч, нийт 6000 орчим тэмдэгтэд барина
    parts = []
    total_target = 6000
    per_doc = max(800, total_target // max(1, len(docs)))
    for d in docs:
        ctx = trim_text(d.get("text", ""), per_doc)
        parts.append(f"- {ctx}")
    context = "\n".join(parts)
    prompt = (
        "Дараах баримтуудыг суурь болгон Монгол хэлээр товч, тодорхой хариу бэлдэнэ үү.\n"
        "Бүрэн итгэлгүй тохиолдолд \"мэдээлэл дутуу\" гэж онцол.\n\n"
        f"Баримтууд:\n{context}\n\n"
        f"Асуулт: {question}\n\n"
        "Хариулт:"
    )
    return prompt

def ollama_generate(prompt: str) -> str:
    """Ollama /api/generate streaming JSON (newline-delimited)"""
    url = f"{OLLAMA_URL}/api/generate"
    payload = {"model": CHAT_MODEL, "prompt": prompt}
    try:
        with requests.post(url, json=payload, stream=True, timeout=120) as r:
            r.raise_for_status()
            answer = []
            for line in r.iter_lines():
                if not line:
                    continue
                try:
                    item = json.loads(line.decode("utf-8"))
                except json.JSONDecodeError:
                    continue
                if "response" in item:
                    answer.append(item["response"])
                # item["done"] == True үед stream өндөрлөнө
            return "".join(answer).strip()
    except requests.RequestException as e:
        raise RuntimeError(f"Ollama generate failed: {e}")

# =========================
# Endpoints
# =========================
@app.get("/health")
def health():
    return {"status": "ok", "qdrant": QDRANT_URL, "ollama": OLLAMA_URL, "collection": COLLECTION_NAME}

@app.post("/add_doc")
def add_doc(doc: Document):
    """Баримт + metadata-г embedding болгоод Qdrant-д хадгална."""
    try:
        vec = embed(doc.text)
        pid = str(uuid.uuid4())
        payload = {"text": doc.text}
        if doc.metadata:
            payload.update(doc.metadata)

        qdrant.upsert(
            collection_name=COLLECTION_NAME,
            points=[rest.PointStruct(id=pid, vector=vec, payload=payload)],
        )
        return {"status": "success", "id": pid, "payload": payload}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/ask")
def ask(q: Query):
    """Асуултыг embedding → Qdrant хайлт → контекст → Ollama хариу."""
    try:
        qvec = embed(q.question)
        hits = qdrant.search(
            collection_name=COLLECTION_NAME,
            query_vector=qvec,
            limit=q.top_k,
            with_payload=True,
        )

        docs = []
        for h in hits:
            docs.append({
                "id": h.id,
                "score": float(h.score),
                "text": (h.payload or {}).get("text", ""),
                "metadata": {k: v for k, v in (h.payload or {}).items() if k != "text"}
            })

        answer = ""
        if docs:
            prompt = build_prompt(q.question, docs)
            try:
                answer = ollama_generate(prompt)
            except Exception as gen_err:
                # Хэрэв Ollama уналаа гээд хайлтын үр дүнг JSON-оор буцаасаар байна
                answer = f"(Анхааруулга) Генерац хийхэд алдаа: {gen_err}"

        return {
            "question": q.question,
            "top_k": q.top_k,
            "answers": docs,          # хайлтын үр дүн
            "generated_answer": answer # Ollama-ийн хариу
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
