from qdrant_client import QdrantClient
from qdrant_client.models import PointStruct, VectorParams, Distance
import requests
import numpy as np

OLLAMA_URL = "http://localhost:11434"
COLLECTION_NAME = "policies"

qc = QdrantClient(url="http://localhost:6333")

def get_embedding(text: str, model_name="nomic-embed-text:latest"):
    """Ollama embedding-ийг гаргах (шинэ JSON бүтэцтэй тааруулсан)"""
    resp = requests.post(f"{OLLAMA_URL}/v1/embeddings", json={
        "model": model_name,
        "input": text
    })
    resp.raise_for_status()
    emb_json = resp.json()
    
    # data list-д 0-р элементийн embedding авах
    embedding_vector = emb_json["data"][0]["embedding"]
    
    import numpy as np
    return np.array(embedding_vector, dtype=np.float32)


def retrieve_docs(question: str, top_k=5):
    """Qdrant-аас semantic search хийж doc-уудыг буцаах"""
    query_vector = get_embedding(question)

    results = qc.search(
        collection_name=COLLECTION_NAME,
        query_vector=query_vector,
        limit=top_k,
        with_payload=True,   # payload-д хадгалагдсан текстийг авах
        # distance=Distance.COSINE  # шаардлагатай бол
    )

    docs = []
    for res in results:
        text = res.payload.get("text")  # payload-д text key-тэй байх ёстой
        if text:
            docs.append(text)
    return docs

# Жишээ ашиглалт
if __name__ == "__main__":
    question = "МТГ гэж юу вэ?"
    docs = retrieve_docs(question)
    print(f"Retrieved {len(docs)} docs:")
    for d in docs:
        print("-", d)
