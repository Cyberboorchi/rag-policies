from qdrant_client import QdrantClient, models
from qdrant_client.http.models import Distance, VectorParams
from pypdf import PdfReader
import requests, os, glob

QDRANT_URL = os.getenv("QDRANT_URL", "http://qdrant:6333")
OLLAMA_URL = os.getenv("OLLAMA_URL", "http://ollama:11434")
COLL = "policies"

qc = QdrantClient(url=QDRANT_URL)

def embed(texts):
    r = requests.post(f"{OLLAMA_URL}/api/embeddings",
                      json={"model": "mistral", "input": texts})
    return [v["embedding"] for v in r.json()["data"]]

# 1) Collection үүсгэх
qc.recreate_collection(
    collection_name=COLL,
    vectors_config=VectorParams(size=768, distance=Distance.COSINE)
)

# 2) PDF уншиж индексжүүлэх
for pdf_file in glob.glob("data/*.pdf"):
    reader = PdfReader(pdf_file)
    for page_num, page in enumerate(reader.pages, start=1):
        text = page.extract_text()
        if not text:
            continue
        chunks = [text[i:i+800] for i in range(0, len(text), 800)]
        vectors = embed(chunks)
        payloads = [
            {"text": chunk, "meta": {"file": os.path.basename(pdf_file), "page": page_num}}
            for chunk in chunks
        ]
        ids = [f"{os.path.basename(pdf_file)}#{page_num}_{i}" for i in range(len(chunks))]
        qc.upsert(collection_name=COLL, points=models.Batch(ids=ids, vectors=vectors, payloads=payloads))

print("📚 PDF-үүд амжилттай индексжлээ!")
