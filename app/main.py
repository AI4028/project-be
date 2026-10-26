from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.db import create_tables
from app.errors import install_error_handlers
from app.routers import kiosk, phone, public, ws


@asynccontextmanager
async def lifespan(_: FastAPI):
    create_tables()  # creates missing tables; existing data is kept
    yield


app = FastAPI(title="Project Backend", lifespan=lifespan)
install_error_handlers(app)
app.include_router(public.router)
app.include_router(phone.router)
app.include_router(kiosk.router)
app.include_router(ws.router)


@app.get("/")
def read_root():
    return {"message": "Project backend is running"}


@app.get("/health")
def health_check():
    return {"status": "ok"}
