"""Publish the bootstrap menu JPEGs before serving their catalog paths from S3."""

from pathlib import Path

from dotenv import load_dotenv


def main() -> None:
    # Deployment commands run outside systemd. Match its backend environment.
    load_dotenv(Path(__file__).resolve().parents[1] / ".env", interpolate=False)
    from app import config, menu_photos

    if not config.MENU_PHOTO_BUCKET:
        print("MENU_PHOTO_BUCKET is unset. Serving bundled sample photos.")
        return
    for photo in sorted(menu_photos.SEED_DIR.glob("*.jpg")):
        menu_photos.upload_jpeg(f"menu/{photo.name}", photo.read_bytes())
        print(f"Published menu/{photo.name}")


if __name__ == "__main__":
    main()
