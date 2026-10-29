import io, os, time
from typing import Optional
import requests
from PIL import Image
import torch, torch.nn as nn
from torchvision import models, transforms
from fastapi import FastAPI, File, UploadFile, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from starlette.responses import JSONResponse
from starlette.concurrency import run_in_threadpool
from urllib.parse import urlsplit
from pathlib import Path
from PIL import UnidentifiedImageError


BASE_DIR = Path(__file__).resolve().parent
MODEL_PATH   = BASE_DIR / "best_model.pth"
CLASSES_PATH = BASE_DIR / "classes.txt"
MAX_IMAGE_BYTES = 8 * 1024 * 1024

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

def predict_image(img: Image.Image):
    t0 = time.time()
    x = preprocess(img).unsqueeze(0)
    with torch.no_grad():
        probs = softmax(model(x)).numpy()[0]
    order = probs.argsort()[::-1]
    top = [{"label": CLASS_NAMES[i], "prob": float(probs[i])} for i in order[:5]]
    return {"label": top[0]["label"], "top_k": top, "model":"resnet50-ft",
            "latency_ms": round((time.time()-t0)*1000)}

def decode_image(content: bytes) -> Image.Image:
    if len(content) > MAX_IMAGE_BYTES:
        raise HTTPException(413, "Choose an image smaller than 8 MB.")
    try:
        with Image.open(io.BytesIO(content)) as image:
            image.load()
            return image.convert("RGB")
    except (UnidentifiedImageError, OSError, ValueError, Image.DecompressionBombError):
        raise HTTPException(415, "This file is not a supported image. Try a JPEG or PNG.")


def load_image_from_url(url: str) -> Image.Image:
    try:
        parts = urlsplit(url)
        valid = parts.scheme in {"https", "http"} and parts.hostname and not parts.username and not parts.password
    except ValueError:
        valid = False
    if not valid:
        raise HTTPException(400, "Enter a complete http:// or https:// image URL.")
    try:
        with requests.get(url, timeout=(5, 10), stream=True) as response:
            if response.status_code != 200:
                raise HTTPException(400, "The image link could not be opened. Try another link or upload the image.")
            content = bytearray()
            for chunk in response.iter_content(65536):
                content.extend(chunk)
                if len(content) > MAX_IMAGE_BYTES:
                    raise HTTPException(413, "Choose an image smaller than 8 MB.")
            return decode_image(bytes(content))
    except requests.Timeout:
        raise HTTPException(504, "The image host took too long to respond. Try uploading the image instead.")
    except requests.RequestException:
        raise HTTPException(502, "The image could not be downloaded. Try another link or upload the image.")


def predict_url(url: str):
    return predict_image(load_image_from_url(url))


def predict_bytes(content: bytes):
    return predict_image(decode_image(content))

@app.post("/predict")
async def predict(
    request: Request,
    file: Optional[UploadFile] = File(None),       # accepts "file"
    upload: Optional[UploadFile] = File(None)      # also accepts "upload"
):
    ctype = request.headers.get("content-type", "")
    if ctype.startswith("application/json"):
        try:
            data = await request.json()
        except ValueError:
            raise HTTPException(400, "The request contains invalid JSON.")
        url = data.get("url") if isinstance(data, dict) else None
        if not isinstance(url, str) or not url.strip():
            raise HTTPException(400, "JSON must include {'url': ...}")
        # A synchronous self-URL fetch must not occupy the ASGI event loop.
        return JSONResponse(await run_in_threadpool(predict_url, url.strip()))

    f = file or upload
    if f is None:
        raise HTTPException(400, "Upload an image file or send JSON {url}")

    try:
        content = await f.read(MAX_IMAGE_BYTES + 1)
    finally:
        await f.close()
    return JSONResponse(await run_in_threadpool(predict_bytes, content))
