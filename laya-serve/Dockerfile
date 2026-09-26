# Laya decision engine served over HTTP (`laya-serve`, TypeSafe Jev-compatible /v1/systemone).
FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    HF_HOME=/models

# CPU-only PyTorch first, so pip does not pull the much larger CUDA build.
RUN pip install --no-cache-dir torch==2.14.0 --index-url https://download.pytorch.org/whl/cpu \
 && pip install --no-cache-dir "laya[serve]==0.3.20"

# Tickets are Polish, so only the multilingual checkpoint is loaded. Preloading happens
# before the server listens, so a healthy container is ready to answer.
ENV LAYA_DEVICE=cpu \
    LAYA_PRELOAD=1 \
    LAYA_MODELS=multilingual \
    LAYA_LOG_LEVEL=warning

EXPOSE 8000

HEALTHCHECK --interval=5s --timeout=5s --start-period=10m --retries=3 \
  CMD ["python", "-c", "import urllib.request; urllib.request.urlopen('http://localhost:8000/health', timeout=4)"]

CMD ["laya-serve"]
