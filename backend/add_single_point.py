# migrate_all_points_optimized.py
import os
import time
import requests
from dotenv import load_dotenv
from qdrant_client import QdrantClient
from qdrant_client.models import PointStruct, VectorParams
from tqdm import tqdm

# Qdrant and Ollama URLs
QDRANT_URL = os.getenv("QDRANT_URL", "http://localhost:6333")
OLLAMA_URL = os.getenv("OLLAMA_URL", "http://localhost:11434")
OLD_COLLECTION = "policies"
NEW_COLLECTION = "policies_mxbai"

# =========================
# Qdrant client
# =========================
try:
    # Initialize the Qdrant client and test the connection
    qc = QdrantClient(url=QDRANT_URL)
    qc.get_collections()
except Exception as e:
    print(f"Error connecting to Qdrant: {e}")
    exit()

# =========================
# Ollama embedding function
# =========================
def get_embedding_ollama(text, retries=3, delay=2):
    """
    Retrieves a single embedding from Ollama with a retry mechanism.
    
    Parameters:
    - text (str): The text to embed.
    - retries (int): Maximum number of retries.
    - delay (int): Delay in seconds between retries.
    """
    for attempt in range(retries):
        try:
            embedding_model = os.getenv("EMBEDDING_MODEL", "mxbai-embed-large")
            payload = {"model": embedding_model, "prompt": text}
            response = requests.post(f"{OLLAMA_URL}/api/embeddings", json=payload, timeout=300)
            response.raise_for_status()
            data = response.json()
            return data["embedding"]
        except Exception as e:
            print(f"[Attempt {attempt+1}] Error with Ollama embedding: {e}")
            time.sleep(delay)
    raise Exception(f"{retries} attempts failed to generate embedding for text.")

# =========================
# Main Migration Logic
# =========================
if __name__ == "__main__":
    print(f"Migrating documents from '{OLD_COLLECTION}' to '{NEW_COLLECTION}'...")
    
    try:
        # Get a single embedding to determine the vector dimension for the new collection
        vec_test = get_embedding_ollama("test text")
        dim = len(vec_test)
        
        # Create the new collection if it doesn't exist
        if not qc.collection_exists(NEW_COLLECTION):
            qc.create_collection(
                collection_name=NEW_COLLECTION,
                vectors_config=VectorParams(size=dim, distance="Cosine")
            )
            print(f"Created new collection '{NEW_COLLECTION}' with dimension {dim}.")
        else:
            print(f"Collection '{NEW_COLLECTION}' already exists.")

        total_processed = 0
        total_points = qc.count(collection_name=OLD_COLLECTION).count
        pbar = tqdm(total=total_points, desc="Migrating documents")
        
        offset = None
        
        while True:
            # Scroll through the old collection in batches
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
                # Retrieve the text from the payload
                doc_text = rec.payload.get("text", "")
                
                if doc_text:
                    try:
                        # Get the new embedding for each document
                        vector = get_embedding_ollama(doc_text)
                        
                        # Create a PointStruct with the new vector and original payload
                        point = PointStruct(
                            id=str(rec.id),
                            vector=vector,
                            payload=rec.payload
                        )
                        points_to_upsert.append(point)
                    except Exception as e:
                        print(f"Skipping point {rec.id} due to embedding error: {e}")
                        continue
            
            if points_to_upsert:
                # Upsert the batch of points to the new collection in a single request
                qc.upsert(
                    collection_name=NEW_COLLECTION,
                    points=points_to_upsert
                )
            
            # Update the progress bar
            total_processed += len(records)
            pbar.update(len(records))

            # Update the offset for the next scroll
            offset = next_offset

        pbar.close()
        print(f"\nMigration successful! Total documents migrated: {total_processed}")
    
    except Exception as e:
        print(f"An error occurred during migration: {e}")