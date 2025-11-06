import io, os, time
from typing import Optional
import requests
from PIL import Image
import torch, torch.nn as nn
from torchvision import models, transforms
from fastapi import FastAPI, File, UploadFile, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from starlette.responses import JSONResponse


MODEL_PATH   = "best_model.pth"
CLASSES_PATH = "classes.txt"

mean=[0.485,0.456,0.406]; std=[0.229,0.224,0.225]
preprocess = transforms.Compose([
    transforms.Lambda(lambda img: img.convert("RGB")),
    transforms.Resize(256), transforms.CenterCrop(224),
    transforms.ToTensor(), transforms.Normalize(mean,std)
])

CLASS_NAMES = [c.strip() for c in open(CLASSES_PATH,encoding="utf-8")]
N = len(CLASS_NAMES)

def build_model(n):
    m = models.resnet50(weights=models.ResNet50_Weights.DEFAULT)
    for p in m.parameters(): p.requires_grad = False
    for p in m.layer3.parameters(): p.requires_grad = True
    for p in m.layer4.parameters(): p.requires_grad = True
    m.fc = nn.Sequential(nn.Dropout(0.5), nn.Linear(m.fc.in_features, n))
    return m

model = build_model(N)
model.load_state_dict(torch.load(MODEL_PATH, map_location="cpu"))
model.eval()
softmax = nn.Softmax(dim=1)

app = FastAPI(title="Game Cover Genre Predictor")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

from fastapi.staticfiles import StaticFiles
from fastapi.responses import RedirectResponse, FileResponse
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent

# mount your project (serves index.html, covers/, etc.) at /ui
app.mount("/ui", StaticFiles(directory=BASE_DIR, html=True), name="ui")

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

def load_image_from_url(url: str) -> Image.Image:
    r = requests.get(url, timeout=10)
    if r.status_code != 200:
        raise HTTPException(400, f"URL status {r.status_code}")
    return Image.open(io.BytesIO(r.content))

@app.post("/predict")
async def predict(
    request: Request,
    file: Optional[UploadFile] = File(None),       # accepts "file"
    upload: Optional[UploadFile] = File(None)      # also accepts "upload"
):
    ctype = request.headers.get("content-type", "")
    if ctype.startswith("application/json"):
        data = await request.json()
        url = (data or {}).get("url")
        if not url:
            raise HTTPException(400, "JSON must include {'url': ...}")
        return JSONResponse(predict_image(load_image_from_url(url)))

    f = file or upload
    if f is None:
        raise HTTPException(400, "Upload an image file or send JSON {url}")

    img = Image.open(io.BytesIO(await f.read()))
    return JSONResponse(predict_image(img))