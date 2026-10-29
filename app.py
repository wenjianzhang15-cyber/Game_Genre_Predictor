import io, os, time
import json
import subprocess
import sys
import threading
from PIL import Image
import torch, torch.nn as nn
from torchvision import models, transforms
from fastapi import FastAPI, Request, HTTPException
from starlette.datastructures import UploadFile
from fastapi.middleware.cors import CORSMiddleware
from starlette.responses import JSONResponse
from starlette.concurrency import run_in_threadpool
from request_limits import RequestLimits
from url_download import validate_url, DownloadError, STATUS_EXIT
from pathlib import Path
from PIL import UnidentifiedImageError


BASE_DIR = Path(__file__).resolve().parent
MODEL_PATH   = BASE_DIR / "best_model.pth"
CLASSES_PATH = BASE_DIR / "classes.txt"
MAX_IMAGE_BYTES = 8 * 1024 * 1024
MAX_IMAGE_PIXELS = 12_000_000
MAX_IMAGE_SIDE = 8192
DOWNLOAD_TIMEOUT_SECONDS = 12
EXAMPLES = {f"/ui/covers/{name}.jpg": BASE_DIR / "covers" / f"{name}.jpg"
            for name in ("HollowKnight", "Stardew", "moncage")}
INFERENCE_SLOT = threading.BoundedSemaphore(1)
torch.set_num_threads(2)

mean=[0.485,0.456,0.406]; std=[0.229,0.224,0.225]
preprocess = transforms.Compose([
    transforms.Lambda(lambda img: img.convert("RGB")),
    transforms.Resize(256), transforms.CenterCrop(224),
    transforms.ToTensor(), transforms.Normalize(mean,std)
])

CLASS_NAMES = [c.strip() for c in open(CLASSES_PATH,encoding="utf-8")]
N = len(CLASS_NAMES)

def build_model(n):
    # The saved state_dict contains every layer; no startup download is needed.
    m = models.resnet50(weights=None)
    for p in m.parameters(): p.requires_grad = False
    for p in m.layer3.parameters(): p.requires_grad = True
    for p in m.layer4.parameters(): p.requires_grad = True
    m.fc = nn.Sequential(nn.Dropout(0.5), nn.Linear(m.fc.in_features, n))
    return m

model = build_model(N)
model.load_state_dict(torch.load(MODEL_PATH, map_location="cpu", weights_only=True))
model.eval()
softmax = nn.Softmax(dim=1)

app = FastAPI(title="Game Cover Genre Predictor")
app.add_middleware(RequestLimits)
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

from fastapi.staticfiles import StaticFiles
from fastapi.responses import RedirectResponse, FileResponse

# Serve only public assets, never source, Git metadata, or model files.
app.mount("/ui/covers", StaticFiles(directory=BASE_DIR / "covers"), name="covers")

@app.get("/ui/index.html", include_in_schema=False)
def index():
    return FileResponse(BASE_DIR / "index.html")

@app.get("/ui", include_in_schema=False)
@app.get("/ui/", include_in_schema=False)
def ui_root():
    return RedirectResponse("/ui/index.html")

# make root redirect to the UI
@app.get("/", include_in_schema=False)
def root():
    return RedirectResponse("/ui/index.html")

@app.get("/health")
def health():
    return {"ok": True, "classes": N}

def _predict_image(img: Image.Image):
    t0 = time.time()
    x = preprocess(img).unsqueeze(0)
    with torch.no_grad():
        probs = softmax(model(x)).numpy()[0]
    order = probs.argsort()[::-1]
    top = [{"label": CLASS_NAMES[i], "prob": float(probs[i])} for i in order[:5]]
    return {"label": top[0]["label"], "top_k": top, "model":"resnet50-ft",
            "latency_ms": round((time.time()-t0)*1000)}

def predict_image(img: Image.Image):
    if not INFERENCE_SLOT.acquire(blocking=False):
        raise HTTPException(503, "The model is busy. Please try again shortly.", headers={"Retry-After": "2"})
    try:
        return _predict_image(img)
    finally:
        INFERENCE_SLOT.release()


def decode_image(content: bytes) -> Image.Image:
    if len(content) > MAX_IMAGE_BYTES:
        raise HTTPException(413, "Choose an image smaller than 8 MB.")
    try:
        with Image.open(io.BytesIO(content)) as image:
            if (image.width * image.height > MAX_IMAGE_PIXELS
                    or max(image.size) > MAX_IMAGE_SIDE):
                raise HTTPException(413, "Use an image up to 12 megapixels and 8192 pixels per side.")
            if image.format not in {"JPEG", "PNG", "WEBP"} or getattr(image, "n_frames", 1) != 1:
                raise HTTPException(415, "Use a single-frame JPEG, PNG or WebP image.")
            image.load()
            return image.convert("RGB")
    except (UnidentifiedImageError, OSError, ValueError, Image.DecompressionBombError):
        raise HTTPException(415, "This file is not a supported image. Try a JPEG or PNG.")


def load_image_from_url(url: str) -> Image.Image:
    if url in EXAMPLES:
        return decode_image(EXAMPLES[url].read_bytes())
    try:
        validate_url(url)
    except DownloadError:
        raise HTTPException(400, "Use a public HTTPS image URL on port 443, without credentials or fragments.") from None
    try:
        completed = subprocess.run(
            [sys.executable, str(BASE_DIR / "url_download.py")],
            input=json.dumps({"url": url}).encode("utf-8"),
            stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
            timeout=DOWNLOAD_TIMEOUT_SECONDS, check=False,
            creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0,
        )
    except subprocess.TimeoutExpired:
        raise HTTPException(504, "The image download exceeded 12 seconds. Try uploading it instead.") from None
    except OSError:
        raise HTTPException(502, "The image could not be downloaded. Try uploading it instead.") from None
    errors = {
        400: "This URL is blocked or does not directly return an image. Use a public HTTPS image link without redirects.",
        413: "Choose an image smaller than 8 MB.",
        415: "The URL must return an uncompressed image response.",
        502: "The image host could not be reached securely. Try uploading the image.",
        504: "The image host took too long. Try uploading the image.",
    }
    if completed.returncode:
        code = next((status for status, exit_code in STATUS_EXIT.items()
                     if exit_code == completed.returncode), 502)
        raise HTTPException(code, errors[code])
    return decode_image(completed.stdout)


def predict_url(url: str):
    with load_image_from_url(url) as image:
        return predict_image(image)


def predict_bytes(content: bytes):
    with decode_image(content) as image:
        return predict_image(image)

@app.post("/predict")
async def predict(request: Request):
    ctype = request.headers.get("content-type", "").split(";")[0].strip().lower()
    if ctype == "application/json":
        try:
            data = await request.json()
        except (ValueError, UnicodeError):
            raise HTTPException(400, "The request contains invalid JSON.")
        url = data.get("url") if isinstance(data, dict) else None
        if not isinstance(url, str) or not url.strip():
            raise HTTPException(400, "JSON must include {'url': ...}")
        return JSONResponse(await run_in_threadpool(predict_url, url.strip()))
    if not ctype:
        raise HTTPException(400, "Upload an image file or send JSON {url}")
    if ctype != "multipart/form-data":
        raise HTTPException(415, "Use a multipart image upload or JSON image URL.")
    async with request.form(max_files=1, max_fields=0, max_part_size=1024) as form:
        f = form.get("file") or form.get("upload")
        if not isinstance(f, UploadFile):
            raise HTTPException(400, "Upload one image using the file field.")
        content = await f.read(MAX_IMAGE_BYTES + 1)
    return JSONResponse(await run_in_threadpool(predict_bytes, content))
