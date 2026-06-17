<div align="center">
  <a href="https://runpod.io?ref=2xxyx4vv&utm_source=github&utm_medium=github&utm_campaign=runpod-paddleocr">
    <img src="https://img.shields.io/badge/RunPod-Hub-9289FE?style=for-the-badge&logo=data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAACAAAAAgCAYAAABzenr0AAAACXBIWXMAAAsTAAALEwEAmpwYAAAAAXNSR0IArs4c6QAAAARnQU1BAACxjwv8YQUAAAIwSURBVHgB7ZbtUcMwDIXfpAuwATCBTMAmsAlhApgAJoAJYALYBCaACWADmMDfB0+WKllO7Di0d+UfnU6WZOlJslME/5pQq9VqERHB6XRqOI7j0lim6bLf71v7/f4cBA5DKeWGIYiCILiOvu87xtgNc2AulUq1HMe5Y4xtrLXkcrlsMQe2LD8iF8wdYwxiAmazGYPZbDbN+Xx+Z4zdG2vn8/mNBw5Bq9VqOOvMOJ1Om91uN4PErVbrlnq9XkcpldOMMc5ms5lhjDWbzXoY6/V6QYxwPB4L2+AFw3EcxhgzTdMMguBOCOGXUqoQQpRSSpeq1Wr13W73sNlsPjLGJq7rNvt6vSZCiIQQQkr5gtBarZYYDodXkiRJjTGktJYkSUie50QIQYIgIMYYx/O8OY7jI5ckQggxxhhijGEYhqPJZNIkSRLGGJvP51dSSkWSJCGEkFKSSpLESZKktVqN9nq9OymlJkmSKKVIIUkipZRSr9stFotbrVarSimKokgkSQ+ovV6vV6/X+0VRHCilb8YYQpIkSimSlJKyLElZlqTf7xNjDEmSdK2UInmeE2MMSSlln0opIoTMGGPEGENEKTWXJIlardYbKaX5fD4bY4gx9gN4Pp9fJ5NJe5f+EEKq0+n8qNvt7qSUZq1WI0mSkKqqSlEUX4uiYFJKSimnrVarjWbbttnr9X6llLqHKqrVqgghCKUUCSF0s9lccRyHFkVBn+u/9Jc4nU5r+B0LIS4YY0oIEf4CR1EUwV9BSSn9A6X/F0n+j8APNUR25mfXGqcAAAAASUVORK5CYII=" alt="RunPod Hub">
  </a>
</div>

# RunPod PaddleOCR-VL Serverless Worker

[![Runpod](https://api.runpod.io/badge/sebudev/runpod-paddleocr)](https://console.runpod.io/hub/sebudev/runpod-paddleocr)
[![PaddleOCR](https://img.shields.io/badge/PaddleOCR-3.7.0-blue)](https://github.com/PaddlePaddle/PaddleOCR)
[![License](https://img.shields.io/badge/License-Apache%202.0-green)](LICENSE)

PaddleOCR-VL-1.6 (0.9B) serverless worker for RunPod. Supports document parsing: OCR, table recognition, formula recognition, chart recognition, text spotting, and seal recognition.

## Project Structure

```
runpod-paddleocr/
├── .runpod/
│   ├── hub.json            # RunPod Hub metadata & config
│   └── tests.json          # Hub test cases
├── Dockerfile              # Docker build instructions (CUDA 12.6)
├── requirements.txt        # Python dependencies
├── .dockerignore           # Build exclusions
├── handler.py              # RunPod serverless handler
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

### Deploy from RunPod Hub (Recommended)

[![Deploy on RunPod](https://img.shields.io/badge/RunPod-Deploy%20on%20Hub-9289FE?style=flat-square)](https://runpod.io?ref=2xxyx4vv&utm_source=github&utm_medium=github&utm_campaign=runpod-paddleocr)

1. Go to the **[RunPod Hub](https://runpod.io?ref=2xxyx4vv)** and search for **PaddleOCR-VL-1.6**
2. Click **Deploy** and configure your endpoint settings
3. Choose a preset or customize environment variables
4. Click **Deploy Endpoint** — RunPod handles the build and deployment automatically

### Manual Deploy from Docker Registry

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
| `use_ocr_for_image_block` | bool | `false` | Extract text from image blocks instead of skipping them |
| `format_block_content` | bool | `true` | Format block content as Markdown (vs raw output) |
| `use_seal_recognition` | bool | `false` | Enable seal/stamp text recognition |

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
| `USE_OCR_FOR_IMAGE_BLOCK` | `false` | Extract text from image blocks (overridable per-job) |
| `FORMAT_BLOCK_CONTENT` | `true` | Format block content as Markdown (overridable per-job) |
| `USE_SEAL_RECOGNITION` | `false` | Enable seal/stamp recognition (overridable per-job or via `seal` task) |

### Performance

| Variable | Default | Description |
|----------|---------|-------------|
| `CONCURRENT_WORKERS` | `1` | Number of concurrent requests per worker. Increase for small/rapid OCR jobs. Monitor GPU memory. |

## Local Testing

```bash
# Test with test_input.json
python handler.py

# Test with custom input
python handler.py --test_input '{"input": {"image": "https://example.com/doc.png"}}'
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
