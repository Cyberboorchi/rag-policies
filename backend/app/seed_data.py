from qdrant_client import QdrantClient
import requests, os
from dotenv import load_dotenv

load_dotenv()
QDRANT_URL = os.getenv("QDRANT_URL", "http://qdrant:6333")
OLLAMA_URL = os.getenv("OLLAMA_URL", "http://ollama:11434")
COLL = os.getenv("COLLECTION_NAME", "policies")

qc = QdrantClient(url=QDRANT_URL)

# Collection үүсгэх
qc.recreate_collection(
    collection_name=COLL,
    vectors_config={"size": 1536, "distance": "Cosine"}
)


documents = [
    "Ажилтны чөлөө авах журам: ...",
    "Төлбөрийн журам: ...",
    "Нууцлалын бодлого: ..."
]

for i, doc in enumerate(documents):
    embedding = requests.post(f"{OLLAMA_URL}/api/embeddings", json={
        "model": "nomic-embed-text",
        "text": doc
    }).json()["embedding"]

    qc.upsert(
        collection_name=COLL,
        points=[{
            "id": i,
            "vector": embedding,
            "payload": {"text": doc}
        }]
    )

print("Документууд Qdrant-д амжилттай нэмэгдлээ.")
