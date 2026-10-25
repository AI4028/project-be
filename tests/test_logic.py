"""Unit tests for the pure rules in app/logic.py."""

from __future__ import annotations

from datetime import datetime, timezone

import pytest
from sqlalchemy.orm.exc import StaleDataError

from app import config
from app.errors import AppError
from app.logic import (
    TOKEN_ALPHABET,
    build_order_lines,
    check_transition,
    generate_token,
    kst_day,
    summarize_order,
    token_matches,
)
from app.service import transact
from tests.conftest import SEED

MENU = SEED["menu"]


def ms(text: str) -> int:
    return int(datetime.fromisoformat(text).replace(tzinfo=timezone.utc).timestamp() * 1000)


def reason(fn, *args):
    with pytest.raises(AppError) as err:
        fn(*args)
    return err.value.reason


def test_tokens_use_unambiguous_alphabet():
    for _ in range(200):
        token = generate_token()
        assert len(token) == config.TOKEN_LENGTH
        assert all(ch in TOKEN_ALPHABET for ch in token)


def test_current_and_previous_tokens_valid_until_expiry():
    now = 1_000_000
    args = ("AAAAAAAA", now + 10, "BBBBBBBB", now + 5)
    assert token_matches("AAAAAAAA", *args, now)
    assert token_matches("BBBBBBBB", *args, now)
    assert not token_matches("BBBBBBBB", *args, now + 5)
    assert not token_matches("CCCCCCCC", *args, now)
    assert not token_matches("AAAAAAAA", None, None, None, None, now)


def test_day_rolls_over_at_midnight_korea_time():
    assert kst_day(ms("2026-10-06T14:59:59")) == "2026-10-06"
    assert kst_day(ms("2026-10-06T15:00:00")) == "2026-10-07"


def test_prices_come_from_the_menu_with_option_surcharges():
    lines, total = build_order_lines(
        MENU,
        [
            {"itemId": "americano", "qty": 2, "options": {"temp": "ice", "size": "large", "extra": ["shot"]}},
            {"itemId": "grapefruit-ade", "qty": 1},
        ],
    )
    assert lines[0]["unitPrice"] == 2500 + 500 + 500
    assert lines[0]["lineTotal"] == 7000
    assert total == 11500
    assert summarize_order(lines) == "아메리카노 (아이스, 라지, 샷 추가) 2개, 자몽에이드 1개"


def test_no_whipped_cream_is_a_real_menu_choice():
    lines, _ = build_order_lines(MENU, [{"itemId": "vanilla-latte", "qty": 1, "options": {"temp": "ice", "whip": "without"}}])
    assert [o["choiceName"] for o in lines[0]["options"]] == ["아이스", "휘핑크림 빼기"]


def test_a_price_sent_by_the_phone_is_ignored():
    _, total = build_order_lines(MENU, [{"itemId": "grapefruit-ade", "qty": 1, "price": 1}])
    assert total == 4500


@pytest.mark.parametrize(
    "items, expected",
    [
        ([], "empty-order"),
        ("not a list", "empty-order"),
        ([{"itemId": "nope", "qty": 1}], "unknown-item"),
        ([{"itemId": "cheesecake", "qty": 1}], "item-unavailable"),
        ([{"itemId": "grapefruit-ade", "qty": 0}], "bad-qty"),
        ([{"itemId": "grapefruit-ade", "qty": 1.5}], "bad-qty"),
        ([{"itemId": "grapefruit-ade", "qty": True}], "bad-qty"),
        ([{"itemId": "grapefruit-ade", "qty": 11}], "bad-qty"),
        ([{"itemId": "americano", "qty": 1, "options": {"size": "large"}}], "missing-option"),
        ([{"itemId": "americano", "qty": 1, "options": {"temp": "lava", "size": "large"}}], "unknown-choice"),
        ([{"itemId": "americano", "qty": 1, "options": {"temp": "ice", "size": "large", "color": "red"}}], "unknown-option"),
        ([{"itemId": "americano", "qty": 1, "options": {"temp": ["ice"], "size": "large"}}], "bad-options"),
        ([{"itemId": "americano", "qty": 1, "options": {"temp": "ice", "size": "large", "extra": "shot"}}], "bad-options"),
        (
            [{"itemId": "americano", "qty": 1, "options": {"temp": "ice", "size": "large", "extra": ["shot", "shot"]}}],
            "bad-options",
        ),
        ([{"itemId": "grapefruit-ade", "qty": 1}] * (config.MAX_LINES_PER_ORDER + 1), "too-many-lines"),
    ],
)
def test_bad_orders_are_rejected_with_a_specific_code(items, expected):
    assert reason(build_order_lines, MENU, items) == expected


def test_order_status_only_moves_forward():
    for current, new in [("submitted", "accepted"), ("accepted", "preparing"), ("preparing", "ready"), ("ready", "picked_up")]:
        check_transition(current, new)
    assert reason(check_transition, "submitted", "ready") == "bad-transition"
    assert reason(check_transition, "picked_up", "cancelled") == "bad-transition"
    assert reason(check_transition, "preparing", "cancelled") == "bad-transition"


def test_transact_retries_when_another_request_changed_the_same_row():
    class FakeDb:
        commits = rollbacks = 0

        def commit(self):
            self.commits += 1

        def rollback(self):
            self.rollbacks += 1

    calls = []

    def fn():
        calls.append(1)
        if len(calls) == 1:
            raise StaleDataError("someone else updated it")
        return "ok"

    db = FakeDb()
    assert transact(db, fn) == "ok"
    assert len(calls) == 2 and db.rollbacks == 1 and db.commits == 1
