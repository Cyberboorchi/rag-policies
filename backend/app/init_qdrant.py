from qdrant_client import QdrantClient
from qdrant_client.http import models as rest
import os

# ===========================
# Config
# ===========================
QDRANT_URL = os.getenv("QDRANT_URL", "http://localhost:6333")
COLLECTION_NAME = "policies"
VECTOR_SIZE = 384  # all-MiniLM-L6-v2 embedding size
DISTANCE = "Cosine"

# ===========================
# Connect to Qdrant
# ===========================
qc = QdrantClient(url=QDRANT_URL)

# ===========================
# Create / recreate collection
# ===========================
def init_collection():
    try:
        if COLLECTION_NAME in [c.name for c in qc.get_collections().collections]:
            print(f"Collection '{COLLECTION_NAME}' exists. Dropping it...")
            qc.delete_collection(collection_name=COLLECTION_NAME)

        print(f"Creating collection '{COLLECTION_NAME}' with vector size {VECTOR_SIZE}...")
        qc.recreate_collection(
            collection_name=COLLECTION_NAME,
            vectors_config=rest.VectorParams(size=VECTOR_SIZE, distance=DISTANCE)
        )
        print("Collection initialized successfully.")
    except Exception as e:
        print("Failed to initialize collection:", e)

if __name__ == "__main__":
    init_collection()
