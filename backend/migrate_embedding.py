# migrate_embeddings.py
import os
import uuid
import time
import requests
from dotenv import load_dotenv
from qdrant_client import QdrantClient
from qdrant_client.models import PointStruct, VectorParams
from tqdm import tqdm

# =========================
# Load environment
# =========================
load_dotenv()

QDRANT_URL = "http://localhost:6333"
OLLAMA_URL = "http://localhost:11434"

OLD_COLLECTION = "policies"          # Gemini embedding-тэй collection
NEW_COLLECTION = "policies_ollama"   # Ollama embedding-тэй collection

# =========================
# Qdrant client
# =========================
qc = QdrantClient(url=QDRANT_URL)

# =========================
# Ollama embedding function with retry
# =========================
def get_query_embedding_ollama(text, retries=3, delay=2):
    for attempt in range(retries):
        try:
            payload = {"model": "llama3:8b", "prompt": text}
            response = requests.post(f"{OLLAMA_URL}/api/embeddings", json=payload, timeout=300)
            response.raise_for_status()
            data = response.json()
            return data["embedding"]
        except Exception as e:
            print(f"[Attempt {attempt+1}] Ollama embedding failed: {e}")
            time.sleep(delay)
    raise Exception(f"Failed to get embedding for text after {retries} retries")

# =========================
# Create new collection if not exists
# =========================
vec_test = get_query_embedding_ollama("test text")
dim = len(vec_test)

if not qc.collection_exists(NEW_COLLECTION):
    qc.create_collection(
        collection_name=NEW_COLLECTION,
        vectors_config=VectorParams(size=dim, distance="Cosine")
    )
    print(f"New collection '{NEW_COLLECTION}' created with dimension {dim}")
else:
    print(f"Collection '{NEW_COLLECTION}' already exists")

# =========================
# Scroll and migrate data with offset & duplicate check
# =========================
# =========================
# Өгөгдлийг шилжүүлэх
# =========================

already_seen = set() # Энэ хувьсагчийг хэрэглэхийн өмнө зарлах ёстой
total_processed = 0
total_points = qc.count(collection_name=OLD_COLLECTION).count
pbar = tqdm(total=total_points, desc="Баримтуудыг шилжүүлж байна")

# Qdrant scroll-ийг зөв ашиглахын тулд offset-ийг зөв тохируулах нь чухал
offset = None

while True:
    records, next_offset = qc.scroll(
        collection_name=OLD_COLLECTION,
        limit=100,
        offset=offset,
        with_payload=True
    )
    
    if not records:
        break

    points_to_upsert = []
    for rec in records:
        if rec.id in already_seen:
            continue
        already_seen.add(rec.id)

        text = rec.payload.get("text", "")
        metadata = {k: v for k, v in rec.payload.items() if k != "text"}
        
        # Эхлээд текстээс embedding үүсгэх
        vec = get_query_embedding_ollama(text)

        points_to_upsert.append(PointStruct(
            id=str(rec.id),
            vector=vec,
            payload={"text": text, **metadata}
        ))

    # Баримтуудыг бөөнөөр оруулах 
    if points_to_upsert:
        qc.upsert(collection_name=NEW_COLLECTION, points=points_to_upsert)


    total_processed += len(points_to_upsert)
    pbar.update(len(points_to_upsert))

    # Дараагийн эргэлт хийхэд offset-ийг шинэчлэх
    offset = next_offset

pbar.close()
print(f"\nMigration completed! Total points migrated: {total_processed}")
