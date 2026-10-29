FROM pytorch/pytorch:2.6.0-cuda12.4-cudnn9-runtime

WORKDIR /home/penlok/app

RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Pre-populate pretrained face model cache
COPY checkpoints/ /root/.cache/torch/checkpoints/
RUN python3 -c "from facenet_pytorch import InceptionResnetV1; InceptionResnetV1(pretrained='vggface2')"

COPY . .

# Symlink /app to /home/penlok/app for path compatibility
RUN ln -s /home/penlok/app /app

EXPOSE 9000

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
  CMD curl -f http://localhost:9000/health || exit 1

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "9000"]
