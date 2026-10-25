from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.db import create_tables
from app.errors import install_error_handlers
from app.routers import kiosk, phone, public, ws


@asynccontextmanager
async def lifespan(_: FastAPI):
    create_tables()  # creates missing tables; existing data is kept
    yield


app = FastAPI(title="Project Backend", lifespan=lifespan)

# Allow CORS for local dev / mobile / browser testing
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

install_error_handlers(app)
app.include_router(public.router)
app.include_router(phone.router)
app.include_router(kiosk.router)
app.include_router(ws.router)

import os
if os.path.exists("frontend"):
    app.mount("/app", StaticFiles(directory="frontend", html=True), name="frontend")



from fastapi.responses import RedirectResponse
from fastapi import Request


@app.get("/")
def read_root(request: Request):
    if "text/html" in request.headers.get("accept", "") and os.path.exists("frontend"):
        return RedirectResponse(url="/app/")
    return {"message": "Project backend is running"}


@app.get("/health")
def health_check():
    return {"status": "ok"}
