"""Issue a kiosk's secret key. Run the seed script first.

    python -m scripts.create_kiosk GK01

The key is printed once (only its hash is stored). Re-running revokes the old key.
"""

from __future__ import annotations

import sys

from sqlalchemy.orm import Session

from app.auth import hash_token, new_kiosk_key
from app.db import SessionLocal, create_tables
from app.models import Kiosk


def issue_kiosk_key(db: Session, kiosk_id: str) -> str:
    kiosk = db.get(Kiosk, kiosk_id)
    if kiosk is None:
        raise ValueError(f"Kiosk {kiosk_id} not found. Run the seed script first.")
    key = new_kiosk_key()
    kiosk.api_key_hash = hash_token(key)
    db.commit()
    return key


def main() -> None:
    if len(sys.argv) != 2:
        sys.exit("Usage: python -m scripts.create_kiosk <KIOSK_ID, e.g. GK01>")
    create_tables()
    with SessionLocal() as db:
        try:
            key = issue_kiosk_key(db, sys.argv[1])
        except ValueError as err:
            sys.exit(str(err))
    print(f"Kiosk {sys.argv[1]} key (shown once, keep it secret):")
    print(key)


if __name__ == "__main__":
    main()
