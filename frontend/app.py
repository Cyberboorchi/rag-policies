# frontend/app.py

from flask import Flask, render_template, request, jsonify
import os
import requests
from datetime import date   
from typing import cast

app = Flask(__name__)

# Docker Compose дотоод сүлжээнд backend service name ашиглана
ASK_URL = os.getenv("BACKEND_URL", "http://backend:8000/ask")

chat_history = []

CHAPTER_MAP = {
    "1": "Нийтлэг үндэслэл",
	"2": "Ажлын байран дахь ялгаварлан гадуурхалт, дарамт, хүчирхийлэл, бэлгийн дарамтыг хориглох",
	"3": "Банкны дотоод үйл ажиллагааны удирдлага, зохион байгуулалт",
	"4": "Ажилтныг ажилд авах, хөдөлмөрийн гэрээ байгуулах",
	"5": "Ажилтныг ажил, албан тушаалд дэвшүүлэх, өөрчлөх, түр шилжүүлэх, сэлгэн ажиллуулах",
	"6": "Ажил олгогч болон ажилтны эрх, үүрэг",
	"7": "Ажлын цаг ашиглалт, амралт, чөлөө олгох",
	"8": "Гэрээсээ, зайнаас, бүтэн бус цагаар, эсхүл дуудлагын цагаар ажиллах үеийн зохицуулалт", 
	"9": "Цалин хөлс, хөнгөлөлт, тэтгэмж олгох",
	"10": "Шагнал, урамшуулал олгох, ажлын гүйцэтгэлийг үнэлэх",
	"11": "Хөдөлмөрийн сахилга, эд хөрөнгийн хариуцлага",
	"12": "Нийт ажилтнуудад хориглох зүйл", 
	"13": "Ажилтны хувийн мэдээлэл авах, боловсруулах, хадгалах, ашиглах",
	"14": "Хөдөлмөрийн гэрээ  дуусгавар болох, ажил хүлээлцэх", 
	"15": "Хөгжлийн бэрхшээлтэй хүнийг хөдөлмөр эрхлүүлэх, оюутныг дагалднаар суралцуулах, дадлага хийлгэх",
	"16": "Дотоод журмын хэрэгжилт, хяналт"
}

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/chat", methods=["POST"])
def chat():
    data = request.get_json(silent=True) or {}
    user_msg = data.get("message")
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
        
        # хэрэглэгчийн сонгосон chapter болон огноог авах
        selected_key: str = request.form.get("chapter") or ""   # ✅ None биш, үргэлж str болно
        created_date = request.form.get("created_date")  # хэрэглэгч сонгосон эсвэл автоматаар өгөгдсөн огноо
        
        # Qdrant-д хадгалахад урт текстийг авна
        chapter_text = CHAPTER_MAP.get(selected_key, "")
        
        # хадгалсаныхаа дараа хуудсыг дахин render хийх
        return render_template(
            "admin.html",
            created_date=created_date,
            selected_chapter=selected_key,
            chapter_text=chapter_text
        )

    # GET үед өнөөдрийн огноог автоматаар дамжуулна
    return render_template(
        "admin.html",
        created_date=date.today().isoformat(),
        selected_chapter=None,
        chapter_text=None
    )



@app.route("/admin/add_doc", methods=["POST"])
def add_doc_admin():
    data = request.get_json(silent=True) or {}
    doc_text = data.get("text")
    chapter_key = data.get("chapter")
    metadata = data.get("metadata", {})

    if not doc_text:
        return jsonify({"error": "Text is required"}), 400
    
    # Qdrant-д хадгалах metadata-д урт текст
    chapter_text = CHAPTER_MAP.get(chapter_key, "")
    metadata["chapter"] = chapter_text

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
