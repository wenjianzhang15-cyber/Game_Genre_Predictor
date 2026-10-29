# Project status — 2026-10-29

## Current workspace

- Local Windows checkout in `game genre predictor`, branch `chore/local-handoff`.
- Verified fork and origin: https://github.com/wenjianzhang15-cyber/Game_Genre_Predictor
- Upstream: https://github.com/Cjmcd23/CSSE_Local_Demo (push URL disabled).
- Original history retained from `fdc02654782ade7e428a9417f5aeb8badc53f534`.
- Cloud commits were not transferred as Git objects. Their source changes were reconstructed from recorded patches and the pinned HF snapshot. The restored backend, frontend and requirements hashes matched the prior cloud records before the new UI changes.
- Removed 31,224 tracked environment files and the stale model pointer in a local cleanup commit. Historical files remain in Git history.
- No remote pushes or deployment changes performed.

## Completed locally

- Restored backend fixes, restricted static routes, tests, setup documentation and verified model downloader.
- Created independent Python 3.12.14 Windows virtual environment; installed Torch 2.3.0+cpu, torchvision 0.18.0+cpu and NumPy 1.26.4.
- Downloaded model from pinned HF revision `085eedcd43b9076a80c1e88e3e2e085a76950aec`; verified 94,387,665 bytes and SHA-256 `5d4b774fa6514e1aba92ede0ad2fba43386141fdbfebfa54b299ef8229e4f3f0`.
- Preserved deployed class order, preprocessing and model weights.
- Added three clickable cover examples, Top-3 score bars, visible keyboard focus, reduced-motion support, mobile CSS and object-URL preview cleanup.
- Retained team attribution and clarified uncalibrated model scores and temporary upload processing.

## Verification

- Windows: **29 tests passed**, one upstream Starlette/AnyIO deprecation warning. Actual local run: `artifacts/windows-regression.xml`.
- Browser clicks: Hollow Knight → platform, Stardew Valley → indie, Moncage → puzzle; each displayed three score rows.
- Browser upload flow passed with HollowKnight.jpg; displayed platform and three scores. No browser console errors observed. At 390px viewport, no horizontal overflow; restored default viewport afterward. Screenshot: `artifacts/local-preview.jpg`.
- Local preview binds only to `127.0.0.1:7860`; logs and PID are under ignored `artifacts/`.
- Original cloud reported 29 passing tests separately; these are not deployment results.

## Remaining before publication

1. Restrict URL destinations and redirects; bound download duration, decoded image size, request bodies and concurrent predictions.
2. Test Docker build (Docker is not installed locally) and hosted cold start.
3. Complete full keyboard interaction review and confirm final team names and publication wording.
4. Review the final branch before authorizing a push or HF deployment. No publication authorization has been inferred.

## Links

- Local preview: http://127.0.0.1:7860/ui/index.html
- Existing public app: https://legend0908-game-genre-demo.hf.space/ui/index.html
- HF Space: https://huggingface.co/spaces/Legend0908/game-genre-demo
