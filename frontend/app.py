from flask import Flask, render_template, request, jsonify
import os
import requests
from datetime import date
from typing import cast, Dict, Any
from sentence_transformers import SentenceTransformer

app = Flask(__name__)

# Backend API-н endpoint-уудыг тохируулна
BACKEND_ASK_URL = os.getenv("BACKEND_URL", "http://backend:8000/ask")
BACKEND_ADD_URL = os.getenv("BACKEND_ADD_URL", "http://backend:8000/add_doc")

try:
    model = SentenceTransformer("paraphrase-multilingual-MiniLM-L12-v2")
except ImportError:
    # Хэрэв sentence_transformers суулгаагүй бол алдаа мэдэгдэл өгнө
    print("Суулгаагүй байна: pip install -U sentence-transformers")
    model = None

chat_history = []

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/chat", methods=["POST"])
def chat():
    """Чатлах хүсэлт боловсруулах endpoint."""
    data = request.get_json(silent=True) or {}
    user_msg = data.get("message")

    if not user_msg:
        return jsonify({"error": "Message is required"}), 400

    chat_history.append({"role": "user", "content": user_msg})
    payload = {"question": user_msg}

    try:
        resp = requests.post(BACKEND_ASK_URL, json=payload, timeout=120)
        resp.raise_for_status()
        backend_data = resp.json()

        generated_answer = backend_data.get("gemini_answer", "Хариу олдсонгүй.")
        retrieved_docs = backend_data.get("retrieved_docs", [])

        # Зөвхөн оноо нь 0.8-аас дээш эсвэл хамааралтай эх сурвалжийг шүүж харуулах
        source_info = ""
        # 0.8-аас дээш оноотой эх сурвалжийг шүүх
        relevant_docs = [d for d in retrieved_docs if d.get('score', 0) > 0.8]
            
        if relevant_docs:
            source_info = "\n\n**Эх сурвалж:**"
            for doc in relevant_docs:
                text_snippet = doc.get('text', '')[:100] + "..."
                score = doc.get('score', 0)
                # metadata-д title байвал түүнийг ашиглах
                title = doc.get('metadata', {}).get('title', 'Гарчиггүй')
                source_info += f"\n- Гарчиг: {title}\n- Тохирол: {score:.4f} \n- Текст: {text_snippet}"

        final_bot_msg = f"{generated_answer}{source_info}"

    except requests.RequestException as e:
        final_bot_msg = f"Алдаа гарлаа: {e}"

    chat_history.append({"role": "assistant", "content": final_bot_msg})
    return jsonify({"reply": final_bot_msg})


@app.route("/admin")
def admin():
    """Админ хуудсыг харуулах endpoint."""
    return render_template(
        "admin.html",
        created_date=date.today().isoformat()
    )

@app.route("/admin/add_doc", methods=["POST"])
def add_doc_admin():
    """Админ хуудаснаас баримт нэмэх хүсэлтийг боловсруулах endpoint."""
    data = cast(Dict[str, Any], request.get_json(silent=True) or {})
    doc_text = data.get("text")    
    metadata = data.get("metadata", {})

    if not doc_text:
        return jsonify({"error": "Text is required"}), 400

    if not model:
        return jsonify({"error": "Embedding model is not loaded."}), 500
    
    # 🆕 Энд текстийг вектор болгож байна
    try:
        doc_vector = model.encode(doc_text).tolist()
    except Exception as e:
        return jsonify({"error": f"Failed to create vector: {e}"}), 500
    


    payload = {
        "text": doc_text, 
        "metadata": metadata,
        "vector": doc_vector  # 🆕 Үүсгэсэн векторыг нэмлээ
    }

    try:
        resp = requests.post(BACKEND_ADD_URL, json=payload, timeout=120)
        resp.raise_for_status()
        return jsonify(resp.json())
    except requests.RequestException as e:
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)