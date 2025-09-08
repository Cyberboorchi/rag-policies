# migrate_all_points.py
import os
import time
import requests
from dotenv import load_dotenv
from qdrant_client import QdrantClient
from qdrant_client.models import PointStruct, VectorParams
from tqdm import tqdm

# =========================
# Орчны хувьсагчдыг дуудах
# =========================
# load_dotenv()

# Qdrant болон Ollama-ийн URL-уудыг орчны хувьсагчаас авах
QDRANT_URL = os.getenv("QDRANT_URL", "http://localhost:6333")
OLLAMA_URL = os.getenv("OLLAMA_URL", "http://localhost:11434")
OLD_COLLECTION = "policies"
NEW_COLLECTION = "policies_ollama"

# =========================
# Qdrant client
# =========================
try:
    qc = QdrantClient(url=QDRANT_URL)
    # Холболтыг шалгах
    qc.get_collections()
except Exception as e:
    print(f"Qdrant-д холбогдоход алдаа гарлаа: {e}")
    exit()

# =========================
# Ollama embedding функц
# =========================
def get_query_embedding_ollama(text, retries=3, delay=2):
    """Ollama-аас embedding-г алдаа гарсан тохиолдолд дахин оролдох функц."""
    for attempt in range(retries):
        try:
            embedding_model = os.getenv("EMBEDDING_MODEL", "llama3:8b")
            payload = {"model": embedding_model, "prompt": text}
            response = requests.post(f"{OLLAMA_URL}/api/embeddings", json=payload, timeout=300)
            response.raise_for_status()
            data = response.json()
            return data["embedding"]
        except Exception as e:
            print(f"[Оролдлого {attempt+1}] Ollama embedding-д алдаа гарлаа: {e}")
            time.sleep(delay)
    raise Exception(f"{retries} удаа оролдсоны дараа текстээс embedding үүсгэхэд алдаа гарлаа")

# =========================
# Баримт шилжүүлэх үндсэн логик
# =========================
if __name__ == "__main__":
    print(f"'{OLD_COLLECTION}' collection-оос '{NEW_COLLECTION}' collection руу бүх баримтыг нэг нэгээр нь шилжүүлж байна.")
    
    try:
        # Шинэ collection-ийг үүсгэх эсвэл байгаа эсэхийг шалгах
        vec_test = get_query_embedding_ollama("test text")
        dim = len(vec_test)
        if not qc.collection_exists(NEW_COLLECTION):
            qc.create_collection(
                collection_name=NEW_COLLECTION,
                vectors_config=VectorParams(size=dim, distance="Cosine")
            )
            print(f"'{NEW_COLLECTION}' нэртэй шинэ collection-ийг {dim} хэмжээтэй үүсгэлээ")
        else:
            print(f"'{NEW_COLLECTION}' нэртэй collection аль хэдийн үүссэн байна")

        total_processed = 0
        total_points = qc.count(collection_name=OLD_COLLECTION).count
        pbar = tqdm(total=total_points, desc="Баримтуудыг шилжүүлж байна")
        
        offset = None

        while True:
            # Scroll функц ашиглан баримтуудыг багцаар авах
            records, next_offset = qc.scroll(
                collection_name=OLD_COLLECTION,
                limit=100, # Олон хүсэлт явуулахгүй тулд багцын хэмжээг хэвээр үлдээлээ
                offset=offset,
                with_payload=True
            )
            if not records:
                break

            for rec in records:
                doc_text = rec.payload.get("text", "")
                metadata = {k: v for k, v in rec.payload.items() if k != "text"}
                
                if doc_text:
                    vec = get_query_embedding_ollama(doc_text)
                    
                    # Нэг баримтыг шууд upsert хийх
                    qc.upsert(
                        collection_name=NEW_COLLECTION,
                        points=[PointStruct(id=str(rec.id), vector=vec, payload={"text": doc_text, **metadata})],
                    )

                total_processed += 1
                pbar.update(1)

            # Дараагийн эргэлт хийхэд offset-ийг шинэчлэх
            offset = next_offset

        pbar.close()
        print(f"\nШилжүүлэлт амжилттай боллоо! Нийт шилжүүлсэн баримтын тоо: {total_processed}")
    
    except Exception as e:
        print(f"Шилжүүлэлтийн явцад алдаа гарлаа: {e}")
