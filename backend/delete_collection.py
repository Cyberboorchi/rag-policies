from qdrant_client import QdrantClient

# Configuration
QDRANT_URL = "http://localhost:6333"
COLLECTION_NAME = "policies"

# Initialize Qdrant client
qc = QdrantClient(url=QDRANT_URL)

# Check if the collection exists before deleting
if qc.collection_exists(collection_name=COLLECTION_NAME):
    qc.delete_collection(collection_name=COLLECTION_NAME)
    print(f"✅ '{COLLECTION_NAME}' collection has been successfully deleted.")
else:
    print(f"ℹ️ Collection '{COLLECTION_NAME}' does not exist.")
