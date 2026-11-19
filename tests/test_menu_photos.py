from io import BytesIO
from urllib.parse import urlparse

import pytest
import requests
from moto import mock_aws
from PIL import Image

from app import config, menu_photos
from scripts.sync_menu_photos import main as sync_samples

BUCKET = "galjido-menu-test"
PATH = "/kiosk/menu/americano/photo"


@pytest.fixture
def bucket(monkeypatch):
    monkeypatch.setattr(config, "MENU_PHOTO_BUCKET", BUCKET)
    monkeypatch.setenv("AWS_DEFAULT_REGION", "us-east-1")
    with mock_aws():
        menu_photos.s3.cache_clear()
        client = menu_photos.s3()
        client.create_bucket(Bucket=BUCKET)
        yield client
        menu_photos.s3.cache_clear()


def item(env):
    menu = env.client.get("/stores/gist-cafe").json()["menu"]
    return next(i for i in menu if i["id"] == "americano")


def test_seed_upload_and_replacement(env, bucket):
    sync_samples()
    before = item(env)
    for sample in menu_photos.SEED_DIR.glob("*.jpg"):
        response = env.client.get(f"/media/menu/{sample.name}", follow_redirects=False)
        assert response.is_redirect
        assert requests.get(response.headers["location"], timeout=5).content == sample.read_bytes()

    picture = BytesIO()
    Image.new("RGB", (1600, 600), "red").save(picture, format="PNG")
    assert env.client.get("/kiosk/state", headers=env.kiosk).json()["photoUploadsEnabled"]
    result = env.client.put(PATH, headers=env.kiosk, content=picture.getvalue())
    assert result.status_code == 200
    url = result.json()["imageUrl"]
    assert item(env) == {**before, "imageUrl": url}
    response = env.client.get(url, follow_redirects=False)
    assert response.headers["cache-control"] == "no-store"
    signed = response.headers["location"]
    assert "X-Amz-Signature" in urlparse(signed).query
    photo = requests.get(signed, timeout=5)
    assert photo.headers["content-type"] == "image/jpeg"
    assert Image.open(BytesIO(photo.content)).size == (1200, 450)
    assert env.client.put(PATH, headers=env.kiosk, content=picture.getvalue()).json() == result.json()
    sync_samples()
    assert item(env)["imageUrl"] == url


def test_upload_failures_preserve_catalog(env, bucket):
    before = item(env)
    raw = (menu_photos.SEED_DIR / "americano.jpg").read_bytes()
    assert env.client.put(PATH, content=raw).status_code == 401
    assert env.client.put(PATH, headers=env.other_kiosk, content=raw).status_code == 404
    assert env.client.put(PATH, headers=env.kiosk, content=b"x" * (1024 * 1024 + 1)).status_code == 413
    assert env.client.put(PATH, headers=env.kiosk, content=b"invalid").status_code == 415
    assert bucket.list_objects_v2(Bucket=BUCKET)["KeyCount"] == 0
    bucket.delete_bucket(Bucket=BUCKET)
    assert env.client.put(PATH, headers=env.kiosk, content=raw).status_code == 503
    assert item(env) == before


def test_upload_disabled_without_bucket(env, monkeypatch):
    monkeypatch.setattr(config, "MENU_PHOTO_BUCKET", "")
    assert not env.client.get("/kiosk/state", headers=env.kiosk).json()["photoUploadsEnabled"]
    assert env.client.put(PATH, headers=env.kiosk, content=b"x").status_code == 503


def test_catalog_survives_unavailable_s3_credentials(env, bucket, monkeypatch):
    from botocore.exceptions import NoCredentialsError

    def unavailable(**kwargs):
        raise NoCredentialsError()

    menu_photos._can_read_sample.cache_clear()
    monkeypatch.setattr(bucket, "head_object", unavailable)
    monkeypatch.setattr(bucket, "put_object", unavailable)
    sync_samples(allow_offline=True)
    with pytest.raises(NoCredentialsError):
        sync_samples()
    assert not env.client.get("/kiosk/state", headers=env.kiosk).json()["photoUploadsEnabled"]
    sample = env.client.get(item(env)["imageUrl"], follow_redirects=False)
    assert sample.status_code == 200 and sample.headers["content-type"] == "image/jpeg"
