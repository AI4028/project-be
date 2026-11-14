import asyncio
from contextlib import asynccontextmanager, suppress

from fastapi import FastAPI
from fastapi.responses import JSONResponse
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from app import db as database
from app.models import Store
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app import config
from app.db import create_tables
from app.errors import install_error_handlers
from app.routers import demo, kiosk, phone, public, ws
from app.maintenance import maintain


@asynccontextmanager
async def lifespan(_: FastAPI):
    create_tables()  # creates missing tables only
    task = asyncio.create_task(maintain(_))
    try:
        yield
    finally:
        task.cancel()
        with suppress(asyncio.CancelledError):
            await task


app = FastAPI(title="Galjido API", lifespan=lifespan)
# Bearer tokens, not cookies, so no credentials needed.
app.add_middleware(CORSMiddleware, allow_origins=config.CORS_ORIGINS, allow_methods=["*"], allow_headers=["*"])
install_error_handlers(app)

for module in (public, phone, kiosk, ws, demo):
    app.include_router(module.router)

if config.FRONTEND_DIR:
    app.mount("/app", StaticFiles(directory=config.FRONTEND_DIR, html=True), name="frontend")


@app.get("/")
def read_root():
    return {"message": "Galjido API is running"}


@app.get("/health")
def health_check():
    return {"status": "ok"}


@app.get("/ready")
def readiness_check():
    """Check database connectivity and the application schema without exposing errors."""
    try:
        with database.SessionLocal() as db:
            db.execute(select(Store.id).limit(1))
    except SQLAlchemyError:
        return JSONResponse(status_code=503, content={"status": "unavailable"})
    return {"status": "ok"}
