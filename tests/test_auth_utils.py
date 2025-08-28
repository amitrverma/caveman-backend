from datetime import timedelta

from app.utils import auth


def test_hash_and_verify_password():
    password = "supersecret"
    hashed = auth.hash_password(password)
    assert auth.verify_password(password, hashed)
    assert not auth.verify_password("wrong", hashed)


def test_create_and_decode_token():
    token = auth.create_access_token({"sub": "user"}, expires_delta=timedelta(minutes=5))
    decoded = auth.decode_token(token)
    assert decoded["sub"] == "user"


def test_decode_token_invalid():
    assert auth.decode_token("invalid-token") is None
