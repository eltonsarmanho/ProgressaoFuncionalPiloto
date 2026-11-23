"""Helpers for the race tests: two units of work on real PostgreSQL and `threading`.

The first unit of work does its writes, then waits on an event while it still holds its row
locks; the second one starts and is seen waiting on a lock in `pg_stat_activity`; only then the
first one is released. No sleep stands in for the synchronization: the loops poll a condition
with a time limit.
"""

import threading
import time
from collections.abc import Callable
from typing import Any

from sqlalchemy import Engine, text

from app.infrastructure.database.repositories import SqlUnitOfWork
from app.infrastructure.database.session import make_session_factory

TIMEOUT = 30.0


class HookedUnitOfWork(SqlUnitOfWork):
    """A unit of work whose scoring-table repository calls `hook(name)` after each method in
    `names` returns, so a test can pause the use case at a known point, locks still held."""

    def __init__(self, session_factory, names: tuple[str, ...], hook: Callable[[str], None]):
        super().__init__(session_factory)
        self._names = names
        self._hook = hook

    def __enter__(self):
        super().__enter__()
        repo = self.scoring_tables
        for name in self._names:
            real = getattr(repo, name)

            def hooked(*args, _real=real, _name=name, **kwargs):
                result = _real(*args, **kwargs)
                self._hook(_name)
                return result

            setattr(repo, name, hooked)
        return self


def hooked_factory(engine: Engine, names: tuple[str, ...], hook: Callable[[str], None]):
    factory = make_session_factory(engine)
    return lambda: HookedUnitOfWork(factory, names, hook)


def blocked_backends(engine: Engine) -> int:
    with engine.connect() as conn:
        return conn.execute(
            text(
                "SELECT count(*) FROM pg_stat_activity "
                "WHERE wait_event_type = 'Lock' AND datname = current_database()"
            )
        ).scalar_one()


def wait_until_blocked(engine: Engine, count: int = 1) -> None:
    """Returns when `count` backends wait on a lock; fails after the time limit."""
    deadline = time.monotonic() + TIMEOUT
    while blocked_backends(engine) < count:
        if time.monotonic() > deadline:
            raise AssertionError("no backend is waiting on a lock")
        time.sleep(0.02)


class Worker:
    """Runs `fn` in a thread; `result` and `error` hold what it returned or raised."""

    def __init__(self, fn: Callable[[], Any]):
        self.result: Any = None
        self.error: BaseException | None = None
        self._fn = fn
        self._thread = threading.Thread(target=self._run, daemon=True)

    def _run(self) -> None:
        try:
            self.result = self._fn()
        except BaseException as exc:  # noqa: BLE001 - handed to the test
            self.error = exc

    def start(self) -> "Worker":
        self._thread.start()
        return self

    def join(self) -> "Worker":
        self._thread.join(timeout=TIMEOUT)
        assert not self._thread.is_alive(), "the worker did not finish"
        return self


class Gate:
    """The first unit of work stops at `hold()` until the test calls `release()`."""

    def __init__(self):
        self.reached = threading.Event()
        self._release = threading.Event()

    def hold(self) -> None:
        self.reached.set()
        assert self._release.wait(timeout=TIMEOUT), "the gate was never released"

    def wait_reached(self) -> None:
        assert self.reached.wait(timeout=TIMEOUT), "the first unit of work never got there"

    def release(self) -> None:
        self._release.set()
