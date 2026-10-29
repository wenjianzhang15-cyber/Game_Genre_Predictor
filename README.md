# Game Genre Predictor

An existing three-person CSSE/MA416 course project being improved for public use and portfolio presentation. A ResNet-50 classifier assigns a game-cover image to one of five labels: `fighting`, `indie`, `platform`, `puzzle`, `sport`.

Original team repository: https://github.com/Cjmcd23/CSSE_Local_Demo

Existing public deployment: https://huggingface.co/spaces/Legend0908/game-genre-demo

This branch is a local reliability handoff. It has not been pushed or deployed. The model is unchanged; no training notebooks have been recovered or recreated.

## Run locally

Use Python 3.11 or 3.12. The deployment uses 3.11; this handoff has passed all 29 regression tests on Windows with Python 3.12.14, as well as the previous Linux run.

Windows PowerShell, from the repository root:

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
.\.venv\Scripts\python.exe scripts/fetch_model.py
.\.venv\Scripts\python.exe -m uvicorn app:app --host 127.0.0.1 --port 7860
```

If Python 3.12 is installed instead, use `py -3.12` on the first line. No environment activation or PowerShell execution-policy change is necessary. On this machine the existing `.venv` is ready; use `scripts/run_local.ps1` to start it. The environment was created using the Python 3.12 runtime bundled with Codex because `py` is not installed.

Linux/macOS shell (the pinned CPU wheels here were tested only on Linux):

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements-dev.txt
.venv/bin/python scripts/fetch_model.py
.venv/bin/python -m uvicorn app:app --host 127.0.0.1 --port 7860
```

On the same machine, open http://127.0.0.1:7860/ui/index.html. To reuse the verified handoff model without downloading it, run the model script with `--source PATH/TO/original_hf/best_model.pth` instead. Do not use the old GitHub LFS pointer as a model.

## Verify

```powershell
$env:OMP_NUM_THREADS = '2'
$env:OPENBLAS_NUM_THREADS = '2'
.\.venv\Scripts\python.exe -m pytest -q
```

Linux: `OMP_NUM_THREADS=2 OPENBLAS_NUM_THREADS=2 .venv/bin/python -m pytest -q`.

The tests use the real saved model, three existing covers, same-server URL requests, bad input, simulated network failures, CORS, and static-file access restrictions. Test evidence uses temporary directories; it does not depend on the original audit-folder layout.

## Files

| File | Purpose |
| --- | --- |
| `app.py` | FastAPI server, preprocessing, model loading, prediction API |
| `index.html` | Existing dark-themed HTML/CSS/JavaScript frontend |
| `covers/` | Original demo cover assets |
| `classes.txt` | Fixed output-label order |
| `scripts/fetch_model.py` | Retrieve or copy the pinned HF weights and verify size/SHA-256 |
| `best_model.pth` | Local ignored model; obtained separately |
| `tests/` | Real-model and failure-handling regression tests |
| `requirements.txt` | CPU deployment dependencies |
| `requirements-dev.txt` | Deployment dependencies plus test tools |
| `Dockerfile` | Original HF Docker startup configuration |
| `PROJECT_STATUS.md` | Current progress, limitations, and next steps |

## API

`POST /predict` accepts either a multipart file named `file` (also accepts `upload`) or JSON `{"url":"https://.../cover.jpg"}`. The response contains `label`, `top_k` (all five labels with `prob` scores), `model`, and `latency_ms`. `GET /health` reports application availability and class count; it is not a full inference test.

The application rejects images larger than 8 MiB after request parsing. The reverse proxy/body-transfer limits have not been reviewed. Upload decoding and URL downloads run away from the async event loop, allowing the server to serve its own cover requests. Only `index.html` and `covers/` are exposed under `/ui`.

## Model provenance and limitations

Pinned HF revision: `085eedcd43b9076a80c1e88e3e2e085a76950aec`.

Model size: 94,387,665 bytes. SHA-256: `5d4b774fa6514e1aba92ede0ad2fba43386141fdbfebfa54b299ef8229e4f3f0`.

Preprocessing remains RGB conversion, Resize(256), CenterCrop(224), tensor conversion, and ImageNet normalization. The full saved state_dict is loaded with `weights_only=True`; no extra ImageNet download is required at startup.

Danny's supplied resume records historical test accuracy of 50.3% versus a 24.1% majority-class baseline. These are original project results, not measurements of this branch. The HF README contains conflicting framework and metric descriptions and is not used as the current setup guide. Scores are uncalibrated model outputs; the model assigns one of its five labels even to unrelated images.

No application-level permanent upload storage was found, but multipart handling can use temporary files. No claim is made about hosting-provider retention or logs.

## Git and publication

The original Git history is preserved. A separate cleanup commit removes the accidentally tracked virtual environment and stale model pointer from the new branch's current tree. The original historical files remain in Git history. New environments, model files, credentials, test outputs, and handoff archives are ignored.

`upstream` is the original team repository, with pushing disabled locally. `origin` points to the verified personal fork `wenjianzhang15-cyber/Game_Genre_Predictor`. Development is on `chore/local-handoff`. Cloud source changes were reconstructed from recorded patches; the unpublished cloud commits themselves were not transferred.

Do not publish the current branch yet: URL destination/redirect restrictions, resource controls, Docker verification, and complete UI acceptance checks remain open. The three clickable examples and Top-3 results have been checked in the local browser. Retrieve the model before any Docker build, and review the image contents. Deployment or new remote pushes require the user's approval.
