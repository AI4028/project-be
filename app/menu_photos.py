"""Private S3 menu photos, exposed to clients through stable catalog URLs."""

import hashlib
import re
from functools import lru_cache
from io import BytesIO
from pathlib import Path

import boto3
from botocore.config import Config
from botocore.exceptions import BotoCoreError, ClientError
from PIL import Image, ImageOps
from starlette.concurrency import run_in_threadpool
from starlette.responses import RedirectResponse
from starlette.staticfiles import StaticFiles

from app import config
from app.errors import AppError

MAX_BYTES = 1024 * 1024
SEED_DIR = config.MEDIA_DIR.parent / "seed" / "menu-photos"
SEED_KEY = re.compile(r"menu/([\w-]+\.jpg)")
UPLOAD_KEY = re.compile(r"menu/uploads/[0-9a-f]{64}\.jpg")


@lru_cache(maxsize=1)
def s3():
    return boto3.client("s3", config=Config(signature_version="s3v4", connect_timeout=3,
                                            read_timeout=5, retries={"total_max_attempts": 2}))


def upload_jpeg(key: str, data: bytes) -> None:
    s3().put_object(Bucket=config.MENU_PHOTO_BUCKET, Key=key, Body=data, ContentType="image/jpeg")


def save_photo(raw: bytes) -> str:
    try:
        with Image.open(BytesIO(raw), formats=["JPEG", "PNG", "WEBP"]) as image:
            if image.width * image.height > 16_000_000:
                raise ValueError("too many pixels")
            image.thumbnail((1200, 1200))
            pixels = ImageOps.exif_transpose(image).convert("RGB")
            pixels.info.clear()  # discard embedded profiles, metadata and comments
            encoded = BytesIO()
            pixels.save(encoded, format="JPEG", quality=85)
    except (OSError, ValueError, SyntaxError, Image.DecompressionBombError) as exc:
        raise AppError("invalid-photo", "Choose a JPEG, PNG or WebP image up to 16 megapixels.") from exc

    data = encoded.getvalue()
    key = f"menu/uploads/{hashlib.sha256(data).hexdigest()}.jpg"
    try:
        upload_jpeg(key, data)
    except (ClientError, BotoCoreError) as exc:
        raise AppError("photo-storage-unavailable", "Menu photo storage is unavailable.") from exc
    return f"/media/{key}"


def signed_photo_url(key: str, method: str) -> str:
    operation = "head_object" if method == "HEAD" else "get_object"
    try:
        return s3().generate_presigned_url(operation, Params={
            "Bucket": config.MENU_PHOTO_BUCKET, "Key": key,
        }, ExpiresIn=900)
    except (ClientError, BotoCoreError) as exc:
        raise AppError("photo-storage-unavailable", "Menu photo storage is unavailable.") from exc


class CatalogMedia(StaticFiles):
    async def get_response(self, path, scope):
        # StaticFiles uses platform-native separators; S3 keys always use "/".
        path = Path(path).as_posix()
        seed = SEED_KEY.fullmatch(path)
        # Serve legacy custom files in place if they predate the S3 namespace.
        if seed and (config.MEDIA_DIR / path).is_file():
            return await super().get_response(path, scope)
        if (seed or UPLOAD_KEY.fullmatch(path)) and scope["method"] in {"HEAD", "GET"}:
            if config.MENU_PHOTO_BUCKET:
                url = await run_in_threadpool(signed_photo_url, path, scope["method"])
                return RedirectResponse(url, headers={"Cache-Control": "no-store"})
            if seed:
                return await StaticFiles(directory=SEED_DIR).get_response(seed[1], scope)
        return await super().get_response(path, scope)
