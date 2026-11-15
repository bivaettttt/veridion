FROM python:3.13-slim AS runtime
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
ARG EMBEDDING_REV=761b726dd34fb83930e26aab4e9ac3899aa1fa78
RUN python -c "from pathlib import Path; from urllib.request import urlretrieve; p=Path('/models/e5'); p.mkdir(parents=True); base='https://huggingface.co/Xenova/multilingual-e5-small/resolve/${EMBEDDING_REV}/'; urlretrieve(base+'tokenizer.json',p/'tokenizer.json'); urlretrieve(base+'onnx/model_quantized.onnx',p/'model.onnx')"
COPY . .
ENV PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1
RUN useradd -u 10001 veridion
USER veridion
CMD ["uvicorn", "veridion.api:app", "--host", "0.0.0.0", "--port", "8000"]
