# qdrant_backup.py
from qdrant_client import QdrantClient
import json
import os
import argparse

QDRANT_URL = os.getenv("QDRANT_URL", "http://localhost:6333")
COLLECTION_NAME = "policies"
BACKUP_FILE = "policies_backup.json"

qc = QdrantClient(url=QDRANT_URL)

def backup_collection(collection_name=COLLECTION_NAME, backup_file=BACKUP_FILE):
    """
    Collection-ийг JSON файлд хадгалах
    """
    print(f"Backing up collection '{collection_name}' to {backup_file}...")
    points = qc.scroll(collection_name=collection_name, with_payload=True, with_vector=True)

    data = []
    for p in points:
        data.append({
            "id": p.id,
            "vector": p.vector,
            "payload": p.payload
        })

    with open(backup_file, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    print(f"Backup complete. Total points: {len(data)}")

def restore_collection(collection_name=COLLECTION_NAME, backup_file=BACKUP_FILE):
    """
    JSON файлнаас collection руу сэргээх
    """
    if not os.path.exists(backup_file):
        print(f"Backup file {backup_file} does not exist!")
        return

    print(f"Restoring collection '{collection_name}' from {backup_file}...")
    with open(backup_file, "r", encoding="utf-8") as f:
        data = json.load(f)

    points_to_upsert = []
    for p in data:
        points_to_upsert.append({
            "id": p["id"],
            "vector": p["vector"],
            "payload": p["payload"]
        })

    # Batch upsert
    batch_size = 100
    for i in range(0, len(points_to_upsert), batch_size):
        batch = points_to_upsert[i:i+batch_size]
        qc.upsert(collection_name=collection_name, points=batch)

    print(f"Restore complete. Total points restored: {len(points_to_upsert)}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Qdrant collection backup & restore")
    parser.add_argument("action", choices=["backup", "restore"], help="Choose action: backup or restore")
    parser.add_argument("--collection", default=COLLECTION_NAME, help="Collection name")
    parser.add_argument("--file", default=BACKUP_FILE, help="Backup file path")

    args = parser.parse_args()

    if args.action == "backup":
        backup_collection(args.collection, args.file)
    elif args.action == "restore":
        restore_collection(args.collection, args.file)
