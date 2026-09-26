FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app ./app

ENV SMTP_HOST=mailhog
ENV SMTP_PORT=1025
ENV MAIL_FROM=router@example.com
ENV OLLAMA_BASE_URL=http://ollama:11434
ENV OLLAMA_MODEL=qwen2.5:3b
ENV OLLAMA_TIMEOUT=180
ENV OLLAMA_NUM_CTX=2048

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
