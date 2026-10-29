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

1. URL restrictions and resource budgets are implemented; review hosting-specific ingress/rate limits before publication.
2. Run `scripts/verify_docker.ps1` after Docker/WSL installation is approved and completed; neither is installed now. Docker build/run and hosted cold start remain unverified.
3. Complete full keyboard interaction review and confirm final team names and publication wording.
4. Review the final branch before authorizing a push or HF deployment. No publication authorization has been inferred.

## Links

- Local preview: http://127.0.0.1:7860/ui/index.html
- Existing public app: https://legend0908-game-genre-demo.hf.space/ui/index.html
- HF Space: https://huggingface.co/spaces/Legend0908/game-genre-demo

## Local hardening update

- HTTPS/public-IP-only URL retrieval, DNS pinning with TLS hostname checks, no redirects/proxies/retries, and a 12-second kill/reap deadline.
- Exact bundled-cover paths preserve examples without loopback requests. External URLs are not fetched again by the browser for preview.
- Pre-parser body bytes/deadline and admission control; single-file multipart; pixel/dimension/frame restrictions; one concurrent inference and two CPU threads.
- **74 tests passed** on Windows, including actual child-process deadline/reaping, private/mixed DNS rejection, redirect rejection, streaming size limits, upload timeout and admission/inference slot behavior. Evidence: `artifacts/security-regression.xml`.
- Actual public HTTPS download from the fork's raw HollowKnight cover succeeded and predicted platform.
- Dockerfile now uses explicit files, UID 1000, build-time model verification, healthcheck and test/production targets. Verification script prepared and PowerShell syntax checked, but no actual Docker build/run has occurred.
- Docker/Podman not found; WSL status explicitly says not installed. Installation question remains pending; no system installation performed.
- No remote pushes or deployment updates.
