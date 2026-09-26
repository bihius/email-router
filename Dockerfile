FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app ./app
COPY data ./data
COPY scripts ./scripts
RUN chmod +x scripts/start-api.sh

ENV SMTP_HOST=mailhog
ENV SMTP_PORT=1025
ENV MAIL_FROM=router@example.com
ENV OLLAMA_BASE_URL=http://ollama:11434
ENV OLLAMA_MODEL=qwen2.5:7b
ENV OLLAMA_TIMEOUT=180
ENV OLLAMA_NUM_CTX=2048
ENV LOG_LEVEL=warning

EXPOSE 8000

CMD ["./scripts/start-api.sh"]
