# PaddleOCR-VL-1.6 RunPod Serverless — Architecture & Implementation Plan

> Implemented on: 2026-06-16
> Model: PaddleOCR-VL-1.6 (0.9B)
> PaddleOCR version: 3.7.0
> RunPod SDK: 1.7+

---

## 1. Project Structure

```
runpod-paddleocr/
├── Dockerfile                   # Build: CUDA 12.4 + PaddlePaddle GPU + PaddleOCR + runpod
├── .dockerignore                # Git/pycache exclusion
├── README.md                    # Full docs: setup, ENV, API, examples
├── requirements.txt             # pip deps (runpod, paddlepaddle-gpu, paddleocr, pillow, requests)
├── builder/
│   └── requirements.txt         # Legacy (same as above)
├── src/
│   └── handler.py               # RunPod handler: init pipeline, process job, return results
├── test_input.json              # Local test fixture
└── docs/
    └── PADDLEOCR_SERVERLESS_PLAN.md   # This file
```

## 2. Dockerfile Strategy

**Base image:** `nvidia/cuda:12.6.3-runtime-ubuntu22.04`

**Why:**
- PaddlePaddle GPU 3.x requires CUDA 12.6 runtime libraries
- `paddlepaddle-gpu` wheels are hosted at PaddlePaddle's custom index (not PyPI)
- `nvidia/cuda` images ship the exact CUDA driver libs needed
- Slimmer than `pytorch/pytorch` base images

**Layers:**
1. System packages: `python3-pip`, `python3-dev`, `wget`, `curl`
2. CUDA compat symlink: `ldconfig /usr/local/cuda-12.6/compat/`
3. `pip install paddlepaddle-gpu==3.3.1 --extra-index-url https://www.paddlepaddle.org.cn/packages/stable/cu126`
4. `pip install -r requirements.txt` (other deps from PyPI)
5. Copy `src/handler.py`
6. Set `ENV` defaults
7. `CMD ["python", "-u", "/app/handler.py"]`

**Multi-stage avoided** because PaddlePaddle ships native `.so` files that must match the runtime CUDA version precisely.

## 3. Handler Design (`src/handler.py`)

### 3.1 Initialization (module level, runs once)

```python
pipeline = PaddleOCRVL(pipeline_version=OS_ENV["PIPELINE_VERSION"])
```

- Loaded once at container start, not per-job
- All config read from environment variables with sensible defaults

### 3.2 Input Resolution

The handler accepts 3 mutually compatible source types:

| Input Key | Type | Source |
|-----------|------|--------|
| `image` | string | Single image URL or base64 data URI |
| `images` | string[] | Array of image URLs or base64 |
| `pdf` | string | PDF URL or base64 |

**Auto-detection logic:**
1. If starts with `http://` or `https://` → download via `requests`
2. If starts with `data:` or looks like base64 → decode and save to temp
3. Otherwise → treat as local filesystem path

### 3.3 Prediction & Output

```python
output = pipeline.predict(local_path)
for res in output:
    if format in ("json", "both"):
        res.save_to_json(...)    → read & embed in response
    if format in ("markdown", "both"):
        res.save_to_markdown(...) → read & embed in response
```

- Each source can produce multiple pages
- Results returned inline as structured JSON
- Temp files cleaned up in `finally` block

### 3.4 Error Handling

- `try/except` wrapping the entire job
- Returns `{"error": "...", "traceback": "..."}` on failure
- RunPod SDK auto-marks job as FAILED on unhandled exceptions

### 3.5 Cleanup

- All downloaded/decoded temp files deleted in `finally`
- Prevents disk fill-up on long-running workers

## 4. Environment Variables (Fully Customizable)

| Variable | Default | Purpose | Category |
|----------|---------|---------|----------|
| `PIPELINE_VERSION` | `v1.6` | Model version (`v1.5` or `v1.6`) | Model |
| `DEFAULT_TASKS` | `auto` | Comma-separated tasks | Model |
| `OUTPUT_FORMAT` | `json` | Output format (`json`/`markdown`/`both`) | Model |
| `MAX_NEW_TOKENS` | `512` | Generation token limit | Model |
| `HF_TOKEN` | (empty) | HuggingFace access token | Auth |
| `MODEL_CACHE_DIR` | (empty) | Custom HF cache path | Storage |
| `CONCURRENT_WORKERS` | `1` | RunPod concurrent handler count | Performance |
| `BUCKET_ENDPOINT_URL` | (empty) | S3 endpoint for result upload | Storage |

All variables can be overridden per-job via the `input` payload, giving maximum flexibility.

## 5. RunPod Console Configuration

| Setting | Value | Rationale |
|---------|-------|-----------|
| GPU | L4 / A5000 / 3090 / A6000 | Model is 0.9B BF16 — fits 24GB+ comfortably |
| Container Disk | 20 GB | Image + model cache need ~10-15 GB |
| Execution Timeout | 300 s | Most documents process in <60s |
| Active Workers | 0 | Cost-efficient; FlashBoot handles cold starts |
| Max Workers | 3 | Adjust based on expected concurrency |
| FlashBoot | Enabled | Faster cold starts |
| Model Cache | `PaddlePaddle/PaddleOCR-VL-1.6` | Zero-cost model pre-loading |

## 6. API Contract

### Request (`POST /runsync` or `POST /run`)

```json
{
  "input": {
    "image": "https://example.com/document.png",
    "tasks": "ocr,table,formula",
    "output_format": "markdown",
    "max_new_tokens": 1024
  }
}
```

### Response (sync)

```json
{
  "status": "completed",
  "results": [
    {
      "source": "https://example.com/document.png",
      "pages": [
        {
          "page": 0,
          "json": { "text": "...", "tables": [...] },
          "markdown": "# Title\n\nContent...",
          "source": "https://example.com/document.png",
          "source_type": "image"
        }
      ]
    }
  ],
  "total_sources": 1,
  "pipeline_version": "v1.6"
}
```

### Error Response

```json
{
  "error": "No input provided. Provide 'image', 'images', or 'pdf'.",
  "traceback": "Traceback (most recent call last):..."
}
```

## 7. Supported PaddleOCR-VL-1.6 Tasks

| Task | Description |
|------|-------------|
| `ocr` | General text recognition |
| `table` | Table structure + cell content recognition |
| `formula` | Mathematical formula recognition |
| `chart` | Chart/diagram understanding |
| `spotting` | Text spotting (detection + recognition) |
| `seal` | Seal/stamp recognition |
| `auto` | Auto-detect document type (default) |

## 8. Deployment Workflow

```
[Write handler] → [Build Docker image] → [Push to registry]
                                           ↓
[Create RunPod Endpoint] ← [Configure env vars] ← [Set GPU/Timeout]
     ↓
[Send API requests] → [Process documents] → [Get structured output]
```

### Commands

```bash
# Build
docker build --platform linux/amd64 -t user/runpod-paddleocr:v1 .

# Push
docker push user/runpod-paddleocr:v1

# Test locally
python src/handler.py --test_input '{"input": {"image": "https://example.com/doc.png"}}'
```

## 9. Cost Optimization Notes

1. **FlashBoot** keeps worker state warm — use instead of active workers
2. **Set execution timeout** to 300s to avoid runaway jobs
3. **Use L4 or 3090** GPUs for best price/performance ratio
4. **Enable model caching** (`PaddlePaddle/PaddleOCR-VL-1.6`) to skip download time
5. **Set `CONCURRENT_WORKERS=1`** initially, increase only if GPU utilization is low

## 10. References

- [PaddleOCR GitHub](https://github.com/PaddlePaddle/PaddleOCR)
- [PaddleOCR-VL-1.6 on HuggingFace](https://huggingface.co/PaddlePaddle/PaddleOCR-VL-1.6)
- [PaddleOCR-VL Documentation](https://www.paddleocr.ai/latest/version3.x/pipeline_usage/PaddleOCR-VL.html)
- [RunPod Serverless Docs](https://docs.runpod.io/serverless/workers/handler-functions)
- [RunPod Dockerfile Guide](https://docs.runpod.io/serverless/workers/create-dockerfile)
- [RunPod Environment Variables](https://docs.runpod.io/serverless/development/environment-variables)
- [RunPod Model Caching](https://docs.runpod.io/serverless/endpoints/model-caching)
