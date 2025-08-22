from qdrant_client import QdrantClient
from qdrant_client.models import PointStruct, VectorParams, Distance
import requests
import uuid
import os

# Configuration
QDRANT_URL = os.getenv("QDRANT_URL")
OLLAMA_URL = os.getenv("OLLAMA_URL", "http://localhost:11434")
COLLECTION_NAME = "policies"
EMBEDDING_DIM = 768  # Set according to the embedding model used

# Initialize Qdrant client
qc = QdrantClient(url=QDRANT_URL)

# Create collection only if it doesn't exist
if not qc.collection_exists(COLLECTION_NAME):
    qc.create_collection(
        collection_name=COLLECTION_NAME,
        vectors_config=VectorParams(
            size=EMBEDDING_DIM,
            distance=Distance.COSINE
        )
    )

# Sample documents to insert
documents = [
    "МЭДЭЭЛЛИЙН ТЕХНОЛОГИЙН ГАЗРЫН АЖИЛЛАХ ЖУРАМ.",
    "Энэхүү журмын зорилго нь Тээвэр хөгжлийн банк цаашид Банк гэх-ны  Мэдээллийн технологийн газар цаашид МТГ гэх-ын зорилго, чиг үүрэг, бүтэц зохион байгуулалтыг тодорхойлох, түүний өдөр тутмын үйл ажиллагааг журамлан тогтооход оршино.",
    "МТГ нь банкны Үйл ажиллагаа хариуцсан гүйцэтгэх захирлын орлогч цаашид ҮАХГЗО гэх-д харьяалагдан үйл ажиллагаа явуулах бие даасан нэгж мөн.",
    "БҮТЭЦ, ЭРХЛЭХ ҮЙЛ АЖИЛЛАГААНЫ ЧИГЛЭЛ.",
    "МТГ нь банкны Гүйцэтгэх захирлын тушаалаар батлагдсан бүтэц, орон тоотойгоор үйл ажиллагаа явуулна.",
    "МТГ нь дараах бүрэлдэхүүнтэй байна. Үүнд: Газрын захирал; Ахлах мэргэжилтэн; Өгөгдлийн сан хөгжүүлэлт хариуцсан мэргэжилтэн; Сүлжээ, систем хариуцсан  мэргэжилтэн; Сүлжээний инженер; Тусламжийн инженер; Програм ашиглалтын мэргэжилтэн."
]

# Function to get embedding from Ollama
def get_embedding(text: str):
    resp = requests.post(f"{OLLAMA_URL}/api/embeddings", json={
        "model": "nomic-embed-text",
        "prompt": text
    })
    if resp.status_code != 200:
        raise Exception(f"Embedding failed: {resp.text}")
    return resp.json()["embedding"]

# Prepare and upsert points
points = []
for doc in documents:
    embedding = get_embedding(doc)
    point_id = str(uuid.uuid4())
    points.append(PointStruct(
        id=point_id,
        vector=embedding,
        payload={"text": doc}
    ))

qc.upsert(collection_name=COLLECTION_NAME, points=points)
print("✅ Баримт бичгүүд амжилттай Qdrant-д орууллаа.")
