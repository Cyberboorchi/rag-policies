Write-Host "=== Ollama Completion Test (Hello) ==="
Invoke-RestMethod -Uri "http://localhost:11434/v1/completions" `
  -Method Post `
  -ContentType "application/json" `
  -Body '{
    "model": "mistral:latest",
    "prompt": "Сайн байна уу? Та хэн бэ?",
    "max_tokens": 100,
    "temperature": 0.2
  }' | ConvertTo-Json -Depth 5

Write-Host "`n=== Ollama Completion Test (Joke in Mongolian) ==="
Invoke-RestMethod -Uri "http://localhost:11434/v1/completions" `
  -Method Post `
  -ContentType "application/json" `
  -Body '{
    "model": "mistral:latest",
    "prompt": "Та монгол хэлээр нэг хөгжилтэй хошигнол хэлээд өгөөч.",
    "max_tokens": 100
  }' | ConvertTo-Json -Depth 5

Write-Host "`n=== Ollama Embedding Test ==="
Invoke-RestMethod -Uri "http://localhost:11434/v1/embeddings" `
  -Method Post `
  -ContentType "application/json" `
  -Body '{
    "model": "nomic-embed-text:latest",
    "input": "Мэдээллийн технологи"
  }' | ConvertTo-Json -Depth 5
