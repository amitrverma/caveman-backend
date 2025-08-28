import asyncio
from sqlalchemy.exc import OperationalError

from app.utils import scheduler


class DummySession:
    async def __aenter__(self):
        return object()

    async def __aexit__(self, exc_type, exc, tb):
        pass


def test_run_safe_success(monkeypatch):
    monkeypatch.setattr(scheduler, "AsyncSessionLocal", lambda: DummySession())

    calls = []

    async def task(db):
        calls.append(db)

    asyncio.run(scheduler.run_safe(task, "success"))
    assert len(calls) == 1


def test_run_safe_retries(monkeypatch):
    monkeypatch.setattr(scheduler, "AsyncSessionLocal", lambda: DummySession())

    async def no_sleep(_):
        pass

    monkeypatch.setattr(scheduler.asyncio, "sleep", no_sleep)

    class Task:
        def __init__(self):
            self.calls = 0

        async def __call__(self, db):
            self.calls += 1
            if self.calls == 1:
                raise OperationalError("stmt", {}, None)

    task = Task()
    asyncio.run(scheduler.run_safe(task, "retry"))
    assert task.calls == 2


def test_run_safe_exception(monkeypatch):
    monkeypatch.setattr(scheduler, "AsyncSessionLocal", lambda: DummySession())

    async def task(db):
        raise ValueError("boom")

    asyncio.run(scheduler.run_safe(task, "error"))


def test_start_scheduler(monkeypatch):
    calls = []

    class DummyScheduler:
        def add_job(self, *args, **kwargs):
            calls.append(("add", args, kwargs))

        def start(self):
            calls.append(("start",))

    monkeypatch.setattr(scheduler, "scheduler", DummyScheduler())
    monkeypatch.setattr(scheduler, "CronTrigger", lambda **kwargs: ("cron", kwargs))

    scheduler.start_scheduler()

    add_calls = [c for c in calls if c[0] == "add"]
    assert len(add_calls) == 3
    assert ("start",) in calls
