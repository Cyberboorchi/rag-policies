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
BATCH_SIZE = 50
offset = 0
total_processed = 0
already_seen = set()  # Duplicate check
total_points = qc.count(collection_name=OLD_COLLECTION).count
pbar = tqdm(total=total_points, desc="Migrating points")

while True:
    result = qc.scroll(
        collection_name=OLD_COLLECTION,
        limit=BATCH_SIZE,
        offset=offset,
        with_payload=True
    )
    records = result[0]
    if not records:
        break

    points_to_upsert = []
    for rec in records:
        if rec.id in already_seen:
            continue
        already_seen.add(rec.id)

        text = rec.payload.get("text", "")
        metadata = {k: v for k, v in rec.payload.items() if k != "text"}
        vec = get_query_embedding_ollama(text)

        points_to_upsert.append(PointStruct(
            id=str(rec.id),
            vector=vec,
            payload={"text": text, **metadata}
        ))
        total_processed += 1
        pbar.update(1)

    # Upsert хийхээс өмнө жагсаалт хоосон эсэхийг шалгах
    if points_to_upsert:
        qc.upsert(collection_name=NEW_COLLECTION, points=points_to_upsert)

    offset += len(records)

pbar.close()
print(f"\nMigration completed! Total points migrated: {total_processed}")
