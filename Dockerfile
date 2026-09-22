FROM python:3.10-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PIP_NO_CACHE_DIR=1

RUN python -m pip install --upgrade pip setuptools wheel

# Install CPU PyTorch from PyPI
RUN pip install --default-timeout=300 --retries 10 \
    torch==2.14.0

COPY requirements.txt .

RUN pip install --default-timeout=300 --retries 10 \
    -r requirements.txt

COPY . .

# Pre-download Sentence Transformer model
RUN python -c "from sentence_transformers import SentenceTransformer; SentenceTransformer('all-MiniLM-L6-v2')"

EXPOSE 8080

CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8080}"]