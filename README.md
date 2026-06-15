# RunPod PaddleOCR-VL Serverless Worker

PaddleOCR-VL-1.6 (0.9B) serverless worker for RunPod. Supports document parsing: OCR, table recognition, formula recognition, chart recognition, text spotting, and seal recognition.

## Project Structure

```
runpod-paddleocr/
├── Dockerfile              # Docker build instructions
├── requirements.txt        # Python dependencies
├── builder/
│   └── requirements.txt    # (legacy) Python dependencies
├── .dockerignore           # Build exclusions
├── src/
│   └── handler.py          # RunPod serverless handler
├── test_input.json         # Local testing fixture
├── README.md               # This file
└── docs/
    └── PADDLEOCR_SERVERLESS_PLAN.md  # Architecture & design plan
```

## Quick Start

### Prerequisites

- Docker
- Docker Hub account (or any container registry)
- RunPod account
- NVIDIA GPU (16GB+ VRAM recommended, 24GB+ for large documents)

### Build & Deploy

```bash
# Build image
docker build --platform linux/amd64 -t yourdockerhub/runpod-paddleocr:v1 .

# Push to registry
docker push yourdockerhub/runpod-paddleocr:v1
```

Then in the **RunPod Console**:
1. Go to **Serverless** → **New Endpoint**
2. Click **Import from Docker Registry**
3. Enter: `docker.io/yourdockerhub/runpod-paddleocr:v1`
4. Configure:
   - **GPU**: L4 / A5000 / 3090 / A6000 (24GB+ recommended)
   - **Container Disk**: 20 GB
   - **Execution Timeout**: 300 seconds
   - **Active Workers**: 0 (or 1 for zero cold start)
   - **FlashBoot**: Enabled
5. Add any [environment variables](#environment-variables) as needed
6. Click **Deploy Endpoint**

## API Usage

### Request Format

```json
{
  "input": {
    "image": "https://example.com/document.png",
    "tasks": "ocr,table,formula",
    "output_format": "markdown"
  }
}
```

### Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `image` | string | - | URL or base64 data URI of an image |
| `images` | string[] | - | Array of image URLs/base64 |
| `pdf` | string | - | URL or base64 data URI of a PDF |
| `tasks` | string | `auto` | Comma-separated tasks: `ocr`, `table`, `formula`, `chart`, `spotting`, `seal`, or `auto` |
| `output_format` | string | `json` | Output format: `json`, `markdown`, or `both` |
| `max_new_tokens` | int | `512` | Maximum generation tokens |

### Response Format

```json
{
  "status": "completed",
  "results": [
    {
      "source": "https://example.com/document.png",
      "pages": [
        {
          "page": 0,
          "json": { ... },
          "markdown": "# Document Title\n\n...",
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

## Environment Variables

All configuration is done via environment variables. Set them in the RunPod console when creating/editing your endpoint.

### Model Configuration

| Variable | Default | Description |
|----------|---------|-------------|
| `PIPELINE_VERSION` | `v1.6` | PaddleOCR-VL pipeline version (`v1.5`, `v1.6`) |
| `DEFAULT_TASKS` | `auto` | Default task list: `ocr`, `table`, `formula`, `chart`, `spotting`, `seal`, `auto` |
| `OUTPUT_FORMAT` | `json` | Default output format: `json`, `markdown`, `both` |
| `MAX_NEW_TOKENS` | `512` | Maximum tokens for text generation |
| `HF_TOKEN` | - | HuggingFace token for gated/private models |
| `MODEL_CACHE_DIR` | - | Custom model cache path (e.g., `/runpod-volume/huggingface-cache`) |

### Performance

| Variable | Default | Description |
|----------|---------|-------------|
| `CONCURRENT_WORKERS` | `1` | Number of concurrent requests per worker. Increase for small/rapid OCR jobs. Monitor GPU memory. |

## Local Testing

```bash
# Test with test_input.json
python src/handler.py

# Test with custom input
python src/handler.py --test_input '{"input": {"image": "https://example.com/doc.png"}}'
```

## Example Client (Python)

```python
import requests
import json

url = "https://api.runpod.ai/v2/YOUR_ENDPOINT_ID/runsync"
headers = {
    "Authorization": "Bearer YOUR_RUNPOD_API_KEY",
    "Content-Type": "application/json"
}
payload = {
    "input": {
        "image": "https://paddle-model-ecology.bj.bcebos.com/paddlex/imgs/demo_image/paddleocr_vl_demo.png",
        "tasks": "ocr,table,formula",
        "output_format": "markdown"
    }
}

resp = requests.post(url, headers=headers, json=payload)
result = resp.json()
print(json.dumps(result, indent=2))
```

## Model Caching (RunPod)

To use RunPod's model caching for faster cold starts:

1. When creating your endpoint, set **Model** to `PaddlePaddle/PaddleOCR-VL-1.6`
2. Set `HF_TOKEN` env variable if required
3. The handler auto-detects cached models at `/runpod-volume/huggingface-cache/`

## Recommended GPU Tiers

| GPU | VRAM | Suitability |
|-----|------|-------------|
| L4 / A5000 / RTX 3090 | 24 GB | Good for most documents |
| A6000 / A40 | 48 GB | Heavy multi-page documents |
| A100 | 80 GB | Batch processing |

## Notes

- Results are returned inline (max 10 MB for `/run`, 20 MB for `/runsync`)
- For large outputs, configure S3 environment variables in RunPod console
- Temporary files are cleaned up automatically after each job
