"""Publish the bootstrap menu JPEGs before serving their catalog paths from S3."""

import argparse
from pathlib import Path

from botocore.exceptions import BotoCoreError, ClientError

from dotenv import load_dotenv


def main(*, allow_offline: bool = False) -> None:
    # Deployment commands run outside systemd. Match its backend environment.
    load_dotenv(Path(__file__).resolve().parents[1] / ".env", interpolate=False)
    from app import config, menu_photos

    if not config.MENU_PHOTO_BUCKET:
        print("MENU_PHOTO_BUCKET is unset. Serving bundled sample photos.")
        return
    for photo in sorted(menu_photos.SEED_DIR.glob("*.jpg")):
        try:
            menu_photos.upload_jpeg(f"menu/{photo.name}", photo.read_bytes())
        except (BotoCoreError, ClientError) as exc:
            if not allow_offline:
                raise
            print(f"Warning: menu photo sync failed ({type(exc).__name__}). "
                  "Bundled photos are available. Check EC2 role access and rerun scripts.sync_menu_photos.")
            return
        print(f"Published menu/{photo.name}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--allow-offline", action="store_true")
    main(allow_offline=parser.parse_args().allow_offline)
