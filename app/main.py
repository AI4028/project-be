from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app import config
from app.db import create_tables
from app.errors import install_error_handlers
from app.routers import demo, kiosk, phone, public, ws


@asynccontextmanager
async def lifespan(_: FastAPI):
    create_tables()  # creates missing tables; existing data is kept
    yield


app = FastAPI(title="Project Backend", lifespan=lifespan)
# Apps authenticate with Bearer tokens, not cookies, so no credentials needed.
app.add_middleware(CORSMiddleware, allow_origins=config.CORS_ORIGINS, allow_methods=["*"], allow_headers=["*"])
install_error_handlers(app)
app.include_router(public.router)
app.include_router(phone.router)
app.include_router(kiosk.router)
app.include_router(ws.router)
app.include_router(demo.router)

if config.FRONTEND_DIR:
    app.mount("/app", StaticFiles(directory=config.FRONTEND_DIR, html=True), name="frontend")


@app.get("/")
def read_root():
    return {"message": "Project backend is running"}


@app.get("/health")
def health_check():
    return {"status": "ok"}
