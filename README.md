# Project Backend

Minimal FastAPI backend. Requires Python 3.10 or newer.

## Run locally (Windows PowerShell)

From the repository folder:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m uvicorn app.main:app --reload
```

Using the virtual environment Python directly does not require activating it.
In VS Code, select `.venv\Scripts\python.exe` as your Python interpreter.

- App: http://127.0.0.1:8000/
- Health check: http://127.0.0.1:8000/health
- Interactive API documentation: http://127.0.0.1:8000/docs

The root endpoint returns `{"message":"Project backend is running"}`.
The health endpoint returns `{"status":"ok"}`.

## Structure

```text
app/
  __init__.py
  main.py          # Application and initial routes
requirements.txt   # Runtime dependencies
```

Keep secrets in a local `.env` file; it is ignored by Git. The app does not yet
load environment files or include a database, authentication, or business logic.

# Git merge convention

want to work on a specific feature: create a feature/(name of the feature) branch (from branch develop):
```
git checkout -b feature/(name of the feature)
```

finished working, merge to develop:
```
git checkout develop
git merge feature/(name of the feature)
```

merging into main is only after develop passess all the checks:
```
git checkout main
git merge develop
```
