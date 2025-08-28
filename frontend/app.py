from flask import Flask, render_template, request, jsonify
import os
import requests
from datetime import date
from typing import cast, Dict, Any

app = Flask(__name__)

# Backend API-н endpoint-уудыг тохируулна
BACKEND_ASK_URL = os.getenv("BACKEND_URL", "http://backend:8000/ask")
BACKEND_ADD_URL = os.getenv("BACKEND_ADD_URL", "http://backend:8000/add_doc")

# Дотоод журмын бүлгүүдийн мэдээлэл
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
    "14": "Хөдөлмөрийн гэрээ дуусгавар болох, ажил хүлээлцэх", 
    "15": "Хөгжлийн бэрхшээлтэй хүнийг хөдөлмөр эрхлүүлэх, оюутныг дагалднаар суралцуулах, дадлага хийлгэх",
    "16": "Дотоод журмын хэрэгжилт, хяналт"
}

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
        chapters=CHAPTER_MAP,
        created_date=date.today().isoformat()
    )

@app.route("/admin/add_doc", methods=["POST"])
def add_doc_admin():
    """Админ хуудаснаас баримт нэмэх хүсэлтийг боловсруулах endpoint."""
    data = cast(Dict[str, Any], request.get_json(silent=True) or {})
    doc_text = data.get("text")
    chapter_key = data.get("chapter")
    metadata = data.get("metadata", {})

    if not doc_text or not chapter_key:
        return jsonify({"error": "Text and chapter are required"}), 400

    chapter_text = CHAPTER_MAP.get(chapter_key, f"Бүлэг {chapter_key}")
    metadata["chapter"] = chapter_text

    payload = {"text": doc_text, "metadata": metadata}

    try:
        resp = requests.post(BACKEND_ADD_URL, json=payload, timeout=10)
        resp.raise_for_status()
        return jsonify(resp.json())
    except requests.RequestException as e:
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)