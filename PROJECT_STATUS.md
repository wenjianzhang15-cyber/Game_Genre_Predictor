# Project status — 2026-10-29

## Published release

- GitHub: https://github.com/wenjianzhang15-cyber/Game_Genre_Predictor
- Both `main` and `chore/local-handoff` contain the tested release and handoff documentation.
- HF Space: https://huggingface.co/spaces/Legend0908/game-genre-demo
- Live app: https://legend0908-game-genre-demo.hf.space/ui/index.html
- HF deployment commit: `77216ec63ad9a93d782d8bc9af80f5000eced9cc`; runtime API confirmed RUNNING at that exact revision.
- Runtime source release: GitHub `7451e2344db5529ffd8f50ef8ceeffa2ebffe9df`; later commits add deployment checks and documentation only.
- Push and HF deployment were explicitly authorized. Existing cpu-basic hardware and access settings were retained. No purchases or paid hardware upgrades.

## Work completed today

- Recovered the earlier cloud work into the local Windows folder. Source changes were reconstructed from recorded patches and the pinned HF snapshot; original cloud Git commit objects were not transferred.
- Preserved original team Git history from `fdc0265`. Fork origin is verified; original team upstream push URL remains disabled.
- Removed 31,224 tracked virtual-environment files and the stale model pointer from the current tree, without rewriting history.
- Created an independent Python 3.12.14 Windows environment and verified the existing 94,387,665-byte model by SHA-256.
- Restored inference/error handling, restricted static-file exposure and regression tests.
- Added three clickable examples, Top-3 score bars, upload preview cleanup, keyboard focus, reduced-motion support and mobile layout adjustments.
- Added HTTPS/public-IP-only URL retrieval, DNS pinning with TLS hostname verification, no redirects/proxies/retries and a 12-second kill/reap deadline.
- Added pre-parser body/deadline/admission limits, single-file multipart, image dimensions/pixels/formats/frame limits, and bounded inference concurrency/CPU threads.
- Installed WSL 2.7.14.0 and per-user Docker Desktop 4.97.0 with permission. Linux engine 29.9.2 started without a reboot.
- Built non-root production/test images. Fixed PowerShell tmpfs argument quoting and verified restrictive container runtime flags.
- Published GitHub branches and uploaded 12 source/configuration files in one HF commit, preserving the existing model and covers.
- Updated HF README to match the FastAPI/ResNet-50 CPU application and preserve Sophia Yang, Danny Zhang and Connor McDonald attribution.

## Verification evidence

- Windows: **74 tests passed**; `artifacts/security-regression.xml`.
- Linux Docker Python 3.11: **74 tests passed**, one upstream Starlette/AnyIO deprecation warning, 4.69 seconds; `artifacts/docker-verification.log`.
- Production container: health, real inference, UID 1000 and absent Git/tests verified with read-only filesystem, 64 MiB tmpfs, 1 GiB memory, 2 CPUs, 64 PIDs, dropped capabilities and no-new-privileges. Temporary containers removed; local images retained.
- All 12 HF uploaded files matched the release content, allowing CRLF/LF normalization; `artifacts/hf-release-verified.json`.
- **11 hosted smoke checks passed**: health, new frontend, three bundled predictions, real upload, two blocked local URLs, three private-file isolation checks; `artifacts/deployment-check.json`.
- Separate hosted public HTTPS download succeeded and classified Hollow Knight as platform; `artifacts/hf-public-url-check.json`.
- Live browser example returned platform with three score rows; `artifacts/hf-live-release.jpg`.
- Local browser mobile check at 390px had no horizontal overflow. Full accessibility audit and load testing are not claimed.

## Model and scope

- No retraining or claimed accuracy improvement. Weights, label order and preprocessing unchanged.
- Model SHA-256: `5d4b774fa6514e1aba92ede0ad2fba43386141fdbfebfa54b299ef8229e4f3f0`.
- Five labels: fighting, indie, platform, puzzle, sport. Scores remain uncalibrated.
- Application resource budgets are deployed. Local Docker runtime flags do not imply identical hosting-level memory/CPU/ingress controls on HF.
- Future work: hosting-specific rate/load testing, idle-to-awake cold-start measurement and complete accessibility review. New deployment startup succeeded in this release.

## Local operation

- Local branch: `chore/local-handoff`.
- Start local preview: `scripts/run_local.ps1`.
- Re-run container verification: `scripts/verify_docker.ps1` (Docker must be running).
- Re-run hosted smoke checks: `.venv/Scripts/python.exe scripts/verify_deployment.py`.
