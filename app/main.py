from fastapi import FastAPI

app = FastAPI(title="Project Backend")


@app.get("/")
def read_root():
    return {"message": "Project backend is running"}


@app.get("/health")
def health_check():
    return {"status": "ok"}
