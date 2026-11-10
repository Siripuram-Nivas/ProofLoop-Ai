from __future__ import annotations

from app.security import create_token, decode_token, hash_password, verify_password


def test_password_hash_roundtrip():
    stored = hash_password("correct horse battery staple")
    assert stored.startswith("scrypt$")
    assert verify_password("correct horse battery staple", stored)
    assert not verify_password("wrong password", stored)


def test_password_hash_is_salted():
    assert hash_password("same-password") != hash_password("same-password")


def test_jwt_roundtrip():
    token = create_token("usr_test", is_guest=True)
    payload = decode_token(token)
    assert payload is not None
    assert payload["sub"] == "usr_test"
    assert payload["guest"] is True


def test_tampered_token_is_rejected():
    token = create_token("usr_test", is_guest=True)
    header, payload, signature = token.split(".")
    tampered = f"{header}.{payload}.{signature[:-2]}AA"
    assert decode_token(tampered) is None


def test_garbage_token_is_rejected():
    assert decode_token("not-a-jwt") is None
