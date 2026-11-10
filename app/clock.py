"""Current time in ms, as a dependency so tests can override it."""

import time


def get_now() -> int:
    return int(time.time() * 1000)
