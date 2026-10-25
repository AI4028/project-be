"""Pure business rules: no database, no web framework. Easy to unit test."""

from __future__ import annotations

import hmac
import re
import secrets
from datetime import datetime, timezone
from typing import Any, Optional

from app import config
from app.errors import AppError

# Crockford base32 without I, L, O, U: unambiguous if read aloud or typed.
TOKEN_ALPHABET = "0123456789ABCDEFGHJKMNPQRSTVWXYZ"
_KIOSK_ID_RE = re.compile(r"^[A-Z0-9]{4}$")
_TOKEN_RE = re.compile(rf"^[{TOKEN_ALPHABET}]{{{config.TOKEN_LENGTH}}}$")


def generate_token(length: int = config.TOKEN_LENGTH) -> str:
    return "".join(secrets.choice(TOKEN_ALPHABET) for _ in range(length))


def check_kiosk_id(kiosk_id: Any) -> str:
    if not isinstance(kiosk_id, str) or not _KIOSK_ID_RE.match(kiosk_id):
        raise AppError("bad-kiosk-id", "Kiosk ID must be 4 characters (A-Z, 0-9).")
    return kiosk_id


def check_token(token: Any) -> str:
    if not isinstance(token, str) or not _TOKEN_RE.match(token):
        raise AppError("bad-token", "Pairing token is malformed.")
    return token


def token_matches(
    token: str,
    current: Optional[str],
    current_expires_at: Optional[int],
    previous: Optional[str],
    previous_expires_at: Optional[int],
    now: int,
) -> bool:
    """Is `token` one of the kiosk's valid tokens? Constant-time comparison."""
    for candidate, expires_at in ((current, current_expires_at), (previous, previous_expires_at)):
        if candidate and expires_at is not None and expires_at > now and hmac.compare_digest(candidate, token):
            return True
    return False


def kst_day(now_ms: int) -> str:
    """'2026-10-08' in Korea time: the key for daily order numbers."""
    return datetime.fromtimestamp((now_ms + config.KST_OFFSET_MS) / 1000, tz=timezone.utc).date().isoformat()


# ---------- menu and order lines ----------


def build_order_lines(menu: list[dict[str, Any]], requested: Any) -> tuple[list[dict[str, Any]], int]:
    """Check the phone's requested lines against the store menu and compute
    every price on the server. The phone never sends prices.

    requested: [{"itemId": "americano", "qty": 1,
                 "options": {"temp": "ice", "extra": ["shot"]}}]
    Returns (lines, total).
    """
    items = {m["id"]: m for m in menu if isinstance(m, dict) and "id" in m}

    if not isinstance(requested, list) or not requested:
        raise AppError("empty-order", "The order has no items.")
    if len(requested) > config.MAX_LINES_PER_ORDER:
        raise AppError("too-many-lines", f"At most {config.MAX_LINES_PER_ORDER} lines per order.")

    lines: list[dict[str, Any]] = []
    for index, req in enumerate(requested, start=1):
        if not isinstance(req, dict):
            raise AppError("bad-line", f"Line {index} is malformed.")
        item = items.get(req.get("itemId")) if isinstance(req.get("itemId"), str) else None
        if item is None:
            raise AppError("unknown-item", f"Line {index}: item not on this menu.")
        if item.get("available") is False:
            raise AppError("item-unavailable", f"{item['name']} is sold out.")

        qty = req.get("qty")
        if not isinstance(qty, int) or isinstance(qty, bool) or not 1 <= qty <= config.MAX_QTY_PER_LINE:
            raise AppError("bad-qty", f"Quantity must be 1-{config.MAX_QTY_PER_LINE}.")

        picked = req.get("options") or {}
        if not isinstance(picked, dict):
            raise AppError("bad-options", f"Line {index}: options are malformed.")
        defs = item.get("options") or []
        known = {d["id"] for d in defs}
        for key in picked:
            if key not in known:
                raise AppError("unknown-option", f"{item['name']}: unknown option.")

        unit_price = item["price"]
        chosen: list[dict[str, Any]] = []
        for d in defs:
            raw = picked.get(d["id"])
            multi = d.get("type") == "multi"
            if raw is None:
                ids: Any = []
            elif multi:
                ids = raw
            else:
                ids = [raw]
            if not isinstance(ids, list) or not all(isinstance(i, str) for i in ids):
                raise AppError("bad-options", f"{item['name']}: {d['name']} is malformed.")
            if len(set(ids)) != len(ids):
                raise AppError("bad-options", f"{item['name']}: {d['name']} has duplicates.")
            if d.get("required") and not ids:
                raise AppError("missing-option", f"{item['name']}: please choose {d['name']}.")
            max_choices = (d.get("maxChoices") or len(d["choices"])) if multi else 1
            if len(ids) > max_choices:
                raise AppError("too-many-choices", f"{item['name']}: too many choices for {d['name']}.")
            for choice_id in ids:
                choice = next((c for c in d["choices"] if c["id"] == choice_id), None)
                if choice is None:
                    raise AppError("unknown-choice", f"{item['name']}: unknown choice for {d['name']}.")
                if choice.get("available") is False:
                    raise AppError("choice-unavailable", f"{item['name']}: {choice['name']} is unavailable.")
                delta = choice.get("priceDelta") or 0
                unit_price += delta
                chosen.append(
                    {
                        "optionId": d["id"],
                        "optionName": d["name"],
                        "choiceId": choice["id"],
                        "choiceName": choice["name"],
                        "priceDelta": delta,
                    }
                )

        lines.append(
            {
                "itemId": item["id"],
                "name": item["name"],
                "nameEn": item.get("nameEn"),
                "qty": qty,
                "options": chosen,
                "unitPrice": unit_price,
                "lineTotal": unit_price * qty,
            }
        )

    return lines, sum(line["lineTotal"] for line in lines)


def summarize_order(lines: list[dict[str, Any]]) -> str:
    """One-line Korean summary for the kiosk screen and the screen reader:
    '아메리카노 (아이스, 라지) 1개, 카페라떼 2개'"""
    parts = []
    for line in lines:
        opts = [o["choiceName"] for o in line["options"]]
        parts.append(f"{line['name']}{' (' + ', '.join(opts) + ')' if opts else ''} {line['qty']}개")
    return ", ".join(parts)


# ---------- order status ----------

STATUS_TRANSITIONS: dict[str, list[str]] = {
    "submitted": ["accepted", "cancelled"],
    "accepted": ["preparing", "cancelled"],
    "preparing": ["ready"],
    "ready": ["picked_up"],
    "picked_up": [],
    "cancelled": [],
}

# Column that records when an order entered each status.
STATUS_TIME_FIELD = {
    "accepted": "accepted_at",
    "preparing": "preparing_at",
    "ready": "ready_at",
    "picked_up": "picked_up_at",
    "cancelled": "cancelled_at",
}


def check_transition(current: str, new: str) -> None:
    if current not in STATUS_TRANSITIONS:
        raise AppError("bad-status", f"Unknown status {current}.")
    if new not in STATUS_TRANSITIONS[current]:
        raise AppError("bad-transition", f"Cannot change an order from {current} to {new}.")
