МЭДЭЭЛЛИЙН ТЕХНОЛОГИЙН ГАЗРЫН АЖИЛЛАХ ЖУРАМ НЭГ. НИЙТЛЭГ ҮНДЭСЛЭЛ 1.1.Энэхүү журмын зорилго нь Тээвэр хөгжлийн банк цаашид Банк гэх-ны  Мэдээллийн технологийн газар цаашид МТГ гэх-ын зорилго, чиг үүрэг, бүтэц зохион байгуулалтыг тодорхойлох, түүний өдөр тутмын үйл ажиллагааг журамлан тогтооход оршино. 1.2.МТГ нь банкны Үйл ажиллагаа хариуцсан гүйцэтгэх захирлын орлогч цаашид ҮАХГЗО гэх-д харьяалагдан үйл ажиллагаа явуулах бие даасан нэгж мөн. 1.3.МТГ-ын үндсэн зорилго нь мэдээллийн технологийн үйл ажиллагааг тасралтгүй, хэвийн явуулах, дотоод гадаад сүлжээ, техник хангамж болон програм хангамжийн хэвийн найдвартай ажиллагааг хангах, шинэ техник технологи нэвтрүүлэх, банкны хэмжээний компьютерийн хэрэглээг удирдах, зохион байгуулах, зохицуулахад оршино.


1. Ollama сервер ажиллаж байгаа эсэхийг шалгах
 
Invoke-RestMethod -Uri "http://localhost:11434/api/tags"
 
2. Ollama серверийг гар аргаар embedding хийх боломжтой эсэхийг шалгах:

Invoke-RestMethod -Uri "http://localhost:11434/api/embeddings" `
  -Method POST `
  -ContentType "application/json" `
  -Body '{ "model": "nomic-embed-text", "prompt": "Тайлангийн түүх" }'


3. Ollama API-г турших


Invoke-WebRequest -Uri "http://localhost:11434/api/embeddings" `
  -Method POST `
  -ContentType "application/json" `
  -Body '{ "model": "nomic-embed-text", "prompt": "тайлан" }'





Invoke-RestMethod -Uri "http://localhost:8000/add-document" `
  -Method POST `
  -ContentType "application/json" `
  -Body '{ "id": 1, "text": "Тайлангийн агуулга нь санхүүгийн мэдээллийг багтаасан болно." }'


Invoke-RestMethod -Uri "http://localhost:8000/add-document" `
  -Method POST `
  -ContentType "application/json" `
  -Body '{ "id": 0, "text": "Тайлангийн хүсэлтийн түүх" }'


Шийдэл: Docker контейнер хоорондын холболт

✅ 1. Docker network-д бүх контейнерүүдийг нэгтгэх

docker network create rag-net


✅ 2. Ollama, Qdrant, FastAPI контейнерүүдийг rag-net сүлжээнд холбох

docker network connect rag-net ollama
docker network connect rag-net qdrant
docker network connect rag-net rag_app


✅ 3. FastAPI апп дотор OLLAMA_URL-ийг http://ollama:11434 болгох
FastAPI код дотор:



Invoke-RestMethod -Uri "http://localhost:8000/ask" `
  -Method POST `
  -ContentType "application/json" `
  -Body '{ "question": "тайлан" }'


