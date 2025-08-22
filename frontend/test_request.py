import requests

ASK_URL = "http://localhost:8000/ask"  # эсвэл Docker Compose-д бол http://backend:8000/ask
payload = {"question": "Мэдээллийн технологи"}

try:
    resp = requests.post(ASK_URL, json=payload, timeout=10)
    resp.raise_for_status()  # 4xx/5xx алдааг raise хийнэ
    data = resp.json()
    print("✅ Response OK!")
    print(data)
except requests.exceptions.RequestException as e:
    print("❌ Request failed:", e)
