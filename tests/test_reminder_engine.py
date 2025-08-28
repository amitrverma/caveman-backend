import asyncio

from app.utils import reminder_engine


class FakeResult:
    def __init__(self, obj):
        self.obj = obj

    def scalars(self):
        return self

    def first(self):
        return self.obj


class FakeSession:
    def __init__(self, obj):
        self.obj = obj

    async def execute(self, stmt):
        return FakeResult(self.obj)


def test_has_spotted_today(monkeypatch):
    db_true = FakeSession(object())
    assert asyncio.run(reminder_engine.has_spotted_today("u1", db_true)) is True

    db_false = FakeSession(None)
    assert asyncio.run(reminder_engine.has_spotted_today("u1", db_false)) is False


def test_has_logged_micro_today(monkeypatch):
    db_true = FakeSession(object())
    assert asyncio.run(reminder_engine.has_logged_micro_today("u1", db_true)) is True

    db_false = FakeSession(None)
    assert asyncio.run(reminder_engine.has_logged_micro_today("u1", db_false)) is False
