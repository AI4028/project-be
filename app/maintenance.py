"""Periodic session cleanup. Database work stays off the event loop."""
import asyncio
import logging

from starlette.concurrency import run_in_threadpool

from app import db, service
from app.clock import get_now
from app.realtime import hub

logger = logging.getLogger(__name__)


def expire(now):
    with db.SessionLocal() as session:
        return service.expire_sessions(session, now)


async def maintain(app):
    while True:
        try:
            clock = app.dependency_overrides.get(get_now, get_now)
            for event in await run_in_threadpool(expire, clock()):
                await hub.publish(event)
        except Exception:
            logger.exception("Session cleanup failed; retrying on the next pass")
        await asyncio.sleep(5)
