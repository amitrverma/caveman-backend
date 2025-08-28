import pytest
from pywebpush import WebPushException

from app.utils import pushnotification
from app.config import settings


class DummyResponse:
    def __init__(self, status_code):
        self.status_code = status_code


def setup_settings(monkeypatch):
    monkeypatch.setattr(settings, "VAPID_PRIVATE_KEY", "key")
    monkeypatch.setattr(settings, "VAPID_CLAIMS_EMAIL", "test@example.com")


def test_send_push_success(monkeypatch):
    setup_settings(monkeypatch)

    def fake_webpush(**kwargs):
        return "ok"

    monkeypatch.setattr(pushnotification, "webpush", lambda **kwargs: fake_webpush(**kwargs))
    result = pushnotification.send_push({"endpoint": "e", "keys": {}}, "data")
    assert result == "ok"


@pytest.mark.parametrize("status", [410, 404, 400, 401, 500])
def test_send_push_failures(monkeypatch, status):
    setup_settings(monkeypatch)

    def fake_webpush(**kwargs):
        raise WebPushException("error", response=DummyResponse(status))

    monkeypatch.setattr(pushnotification, "webpush", lambda **kwargs: fake_webpush(**kwargs))
    result = pushnotification.send_push({"endpoint": "e", "keys": {}}, "data")
    assert result is None
