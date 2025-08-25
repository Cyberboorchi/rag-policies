# frontend/app.py

from flask import Flask, render_template, request, jsonify
import os
import requests
from datetime import date   

app = Flask(__name__)

# Docker Compose дотоод сүлжээнд backend service name ашиглана
ASK_URL = os.getenv("BACKEND_URL", "http://backend:8000/ask")

chat_history = []

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/chat", methods=["POST"])
def chat():
    user_msg = request.json.get("message")
    print("User message:", user_msg)

    if not user_msg:
        return jsonify({"error": "Message is required"}), 400
    
    # Хэрэглэгчийн мессежийг түүхэнд нэмнэ
    chat_history.append({"role": "user", "content": user_msg})

    payload = {"question": user_msg}

    try:
        resp = requests.post(ASK_URL, json=payload, timeout=10)
        resp.raise_for_status()
        data = resp.json()
        
        print("Backend response:", data)

        # Qdrant / RAG JSON structure-д нийцүүлсэн хандалт
        answers = data.get("json", {}).get("answers", [])
        bot_msg = answers[0]["text"] if answers else "Хариу олдсонгүй"

    except requests.RequestException as e:
        bot_msg = f"Алдаа гарлаа: {e}"

    chat_history.append({"role": "assistant", "content": bot_msg})
    return jsonify({"reply": bot_msg})

@app.route("/admin", methods=["GET", "POST"])
def admin():
    if request.method == "POST":
        created_date = request.form.get("created_date")  # хэрэглэгч сонгосон эсвэл автоматаар өгөгдсөн огноо
        
        # хадгалсаныхаа дараа хуудсыг дахин render хийх
        return render_template("admin.html", created_date=created_date)

    # GET үед өнөөдрийн огноог автоматаар дамжуулна
    return render_template("admin.html", created_date=date.today().isoformat())



@app.route("/admin/add_doc", methods=["POST"])
def add_doc_admin():
    doc_text = request.json.get("text")
    metadata = request.json.get("metadata", {})

    if not doc_text:
        return jsonify({"error": "Text is required"}), 400

    payload = {"text": doc_text, "metadata": metadata}

    try:
        resp = requests.post(
            os.getenv("BACKEND_ADD_URL", "http://backend:8000/add_doc"),
            json=payload, timeout=10
        )
        return jsonify(resp.json())
    except Exception as e:
        return jsonify({"error": str(e)})



if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
