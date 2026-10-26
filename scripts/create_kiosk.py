"""Create (or replace) the secret key a kiosk app uses to sign in.

    python -m scripts.create_kiosk GK01

Prints the key ONCE. Put it in the kiosk app's settings; it cannot be
shown again (only its hash is stored). Running this again makes a new key
and the old one stops working. Run the seed script first.
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
