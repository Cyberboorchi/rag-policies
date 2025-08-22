FROM python:3.10-slim

# Ингестийн ажиллах директор
WORKDIR /ingest

# Одоогийн фолдерын файлуудыг контейнер руу хуулна
COPY . /ingest

# Хамааралтай багцуудыг суулгана
RUN pip install --no-cache-dir -r requirements.txt

# Скрипт нэг удаа ажиллана
CMD ["python", "ingest.py"]
