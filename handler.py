import os
import json
import base64
import tempfile
import logging
import traceback
from urllib.parse import urlparse

import runpod
import requests

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger("paddleocr-handler")

PIPELINE_VERSION = os.environ.get("PIPELINE_VERSION", "v1.6")
DEFAULT_TASKS = os.environ.get("DEFAULT_TASKS", "auto")
OUTPUT_FORMAT = os.environ.get("OUTPUT_FORMAT", "json")
MAX_NEW_TOKENS = int(os.environ.get("MAX_NEW_TOKENS", "512"))
HF_TOKEN = os.environ.get("HF_TOKEN", None)
MODEL_CACHE_DIR = os.environ.get("MODEL_CACHE_DIR", None)
CONCURRENT_WORKERS = int(os.environ.get("CONCURRENT_WORKERS", "1"))

pipeline = None

_REMOTE_URL_HEADERS = {"User-Agent": "RunPod-PaddleOCR/1.0"}
if HF_TOKEN:
    _REMOTE_URL_HEADERS["Authorization"] = f"Bearer {HF_TOKEN}"


def _safe_int(val, default):
    try:
        return int(val)
    except (ValueError, TypeError):
        return default


MAX_NEW_TOKENS = _safe_int(os.environ.get("MAX_NEW_TOKENS"), 512)
CONCURRENT_WORKERS = _safe_int(os.environ.get("CONCURRENT_WORKERS"), 1)


def download_file(url, dest_path=None):
    created = False
    if dest_path is None:
        fd, dest_path = tempfile.mkstemp(suffix=os.path.splitext(urlparse(url).path)[1] or ".png")
        os.close(fd)
        created = True

    try:
        logger.info("Downloading %s -> %s", url, dest_path)
        resp = requests.get(url, headers=_REMOTE_URL_HEADERS, stream=True, timeout=300)
        resp.raise_for_status()
        with open(dest_path, "wb") as f:
            for chunk in resp.iter_content(chunk_size=8192):
                f.write(chunk)
        return dest_path
    except Exception:
        if created and os.path.exists(dest_path):
            try:
                os.remove(dest_path)
            except Exception:
                pass
        raise


def save_base64_to_file(b64_data):
    if "," in b64_data:
        b64_data = b64_data.split(",", 1)[1]
    fd, path = tempfile.mkstemp(suffix=".png")
    os.close(fd)
    try:
        with open(path, "wb") as f:
            f.write(base64.b64decode(b64_data))
        return path
    except Exception:
        if os.path.exists(path):
            try:
                os.remove(path)
            except Exception:
                pass
        raise


def is_url(s):
    if not isinstance(s, str):
        return False
    return s.startswith(("http://", "https://"))


def is_base64(s):
    if not isinstance(s, str):
        return False
    return s.startswith("data:") or _looks_like_base64(s)


def _looks_like_base64(s):
    if not s or len(s) < 50:
        return False
    try:
        chunk = s[:100]
        padding = 4 - len(chunk) % 4 if len(chunk) % 4 else 0
        base64.b64decode(chunk + "=" * padding)
        return True
    except Exception:
        return False


def resolve_input_source(job_input):
    sources = []
    image = job_input.get("image")
    images = job_input.get("images")
    pdf = job_input.get("pdf")

    if image:
        sources.append(("image", image))
    if images:
        for img in images:
            sources.append(("image", img))
    if pdf:
        sources.append(("pdf", pdf))
    return sources


def prepare_file(source_type, source_value):
    if is_url(source_value):
        return download_file(source_value)
    elif is_base64(source_value):
        return save_base64_to_file(source_value)
    else:
        if os.path.exists(source_value):
            return source_value
        raise FileNotFoundError(f"Input path does not exist: {source_value}")


def parse_tasks(tasks_str):
    if not tasks_str or tasks_str.strip().lower() == "auto":
        return {}

    task_list = [t.strip().lower() for t in tasks_str.split(",")]
    kwargs = {}

    has_chart = "chart" in task_list
    has_seal = "seal" in task_list
    has_ocr = "ocr" in task_list
    has_table = "table" in task_list
    has_formula = "formula" in task_list
    has_spotting = "spotting" in task_list

    kwargs["use_chart_recognition"] = has_chart
    kwargs["use_seal_recognition"] = has_seal

    if has_ocr and not has_table and not has_formula and not has_chart and not has_seal and not has_spotting:
        kwargs["use_layout_detection"] = False

    return kwargs


def initialize_pipeline():
    global pipeline
    try:
        from paddleocr import PaddleOCRVL

        logger.info("Initializing PaddleOCRVL (version=%s, cache_dir=%s)",
                     PIPELINE_VERSION, MODEL_CACHE_DIR or "default")
        pipeline = PaddleOCRVL(pipeline_version=PIPELINE_VERSION)

        warmup_path = os.path.join(tempfile.gettempdir(), "_warmup.png")
        if not os.path.exists(warmup_path):
            try:
                from PIL import Image
                img = Image.new("RGB", (64, 64), color="white")
                img.save(warmup_path)
            except Exception:
                warmup_path = None

        if warmup_path and os.path.exists(warmup_path):
            try:
                logger.info("Running warmup inference...")
                pipeline.predict(warmup_path, max_new_tokens=16)
                logger.info("Warmup inference completed")
            except Exception:
                logger.info("Warmup skipped (expected on first run)")

        logger.info("Pipeline initialized successfully")
    except Exception as e:
        logger.error("Failed to initialize pipeline: %s", e)
        raise


def handler(job):
    job_id = job["id"]
    job_input = job["input"]
    logger.info("Processing job %s", job_id)

    output_format = (job_input.get("output_format") or OUTPUT_FORMAT).lower()
    tasks_str = job_input.get("tasks") or DEFAULT_TASKS
    max_new_tokens = _safe_int(job_input.get("max_new_tokens"), MAX_NEW_TOKENS)

    task_kwargs = parse_tasks(tasks_str)

    runpod.serverless.progress_update(job, "Resolving input sources")
    sources = resolve_input_source(job_input)
    if not sources:
        return {"error": "No input provided. Provide 'image', 'images', or 'pdf'."}

    all_results = []
    temp_files = []

    try:
        for idx, (source_type, source_val) in enumerate(sources):
            runpod.serverless.progress_update(
                job, f"Processing source {idx + 1}/{len(sources)}"
            )
            local_path = prepare_file(source_type, source_val)
            temp_files.append(local_path)

            logger.info("Predicting on %s", local_path)
            output = pipeline.predict(
                local_path,
                max_new_tokens=max_new_tokens,
                **task_kwargs,
            )
            page_results = []

            for res in output:
                entry = {"page": len(page_results)}

                if output_format in ("json", "both"):
                    json_path = f"{local_path}_page{len(page_results)}.json"
                    res.save_to_json(save_path=json_path)
                    temp_files.append(json_path)
                    with open(json_path, "r") as f:
                        entry["json"] = json.load(f)

                if output_format in ("markdown", "both"):
                    md_path = f"{local_path}_page{len(page_results)}.md"
                    res.save_to_markdown(save_path=md_path)
                    temp_files.append(md_path)
                    with open(md_path, "r") as f:
                        entry["markdown"] = f.read()

                entry["source"] = source_val
                entry["source_type"] = source_type
                page_results.append(entry)

            all_results.append({"source": source_val, "pages": page_results})

        runpod.serverless.progress_update(job, "Processing complete")

        return {
            "status": "completed",
            "results": all_results,
            "total_sources": len(sources),
            "pipeline_version": PIPELINE_VERSION,
        }

    except Exception as e:
        logger.error("Job %s failed: %s", job_id, traceback.format_exc())
        return {"error": str(e), "traceback": traceback.format_exc()}

    finally:
        for f in temp_files:
            try:
                if os.path.exists(f):
                    os.remove(f)
            except Exception:
                pass


if __name__ == "__main__":
    logger.info(
        "Starting PaddleOCR-VL serverless handler (version=%s, tasks=%s, format=%s)",
        PIPELINE_VERSION, DEFAULT_TASKS, OUTPUT_FORMAT
    )

    if MODEL_CACHE_DIR:
        os.makedirs(MODEL_CACHE_DIR, exist_ok=True)

    initialize_pipeline()

    runpod.serverless.start(
        {
            "handler": handler,
            "concurrency_modifier": lambda x: CONCURRENT_WORKERS,
        }
    )
