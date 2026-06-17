FROM nvidia/cuda:12.6.3-runtime-ubuntu22.04

RUN apt-get update -y \
    && apt-get install -y python3-pip python3-dev wget curl libgl1-mesa-glx libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

RUN ldconfig /usr/local/cuda-12.6/compat/ 2>/dev/null || true
RUN update-alternatives --install /usr/bin/python python /usr/bin/python3 1

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip setuptools wheel \
    && pip install --no-cache-dir -r requirements.txt \
    && pip install --no-cache-dir \
        --extra-index-url https://www.paddlepaddle.org.cn/packages/stable/cu126 \
        paddlepaddle-gpu==3.3.1 \
    && rm -rf /root/.cache/pip

COPY handler.py .
ENV PIPELINE_VERSION=v1.6
ENV DEFAULT_TASKS=auto
ENV OUTPUT_FORMAT=json
ENV MAX_NEW_TOKENS=512
ENV CONCURRENT_WORKERS=1
ENV HF_TOKEN=
ENV MODEL_CACHE_DIR=
ENV PADDLE_PDX_DISABLE_MODEL_SOURCE_CHECK=true

CMD ["python", "-u", "/app/handler.py"]
