# Project working rules

- Continue the existing three-person course project; preserve team credit and Git history.
- Read PROJECT_STATUS.md before editing. Do not retrain, change the class order, or change preprocessing by default.
- Use Python 3.11 or 3.12 in a project virtual environment. Never commit environments, credentials, caches, or model binaries.
- Get the verified model using scripts/fetch_model.py. Do not substitute the old GitHub LFS pointer or disable restricted weight loading.
- Run focused tests after functional changes; distinguish actual results from earlier audit evidence.
- Keep public static routes limited to index.html and covers/. Do not expose the repository directory.
- Keep development local/on a feature branch. Do not push new changes, modify the original team's repository, deploy to HF, purchase services, or change access permissions without the user's explicit authorization for that action.
- Fork creation was authorized, but must use the user's verified GitHub identity. Never invent origin from the HF username.
- Update PROJECT_STATUS.md with completed work, remaining checks, and concrete blockers.
