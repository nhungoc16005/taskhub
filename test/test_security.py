import pytest

from app.core.constants import ACCESS_TOKEN_TYPE, REFRESH_TOKEN_TYPE
from app.core.security import (
    TokenError,
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_password,
    verify_password,
)


def test_hash_is_not_plaintext_and_verifies():
    hashed = hash_password("12345678")
    assert hashed != "12345678"
    assert verify_password("12345678", hashed)
    assert not verify_password("wrong", hashed)


def test_hash_uses_random_salt():
    assert hash_password("12345678") != hash_password("12345678")


def test_access_token_roundtrip():
    payload = decode_token(create_access_token(7), ACCESS_TOKEN_TYPE)
    assert payload["sub"] == "7" and payload["type"] == ACCESS_TOKEN_TYPE


def test_wrong_token_type_is_rejected():
    with pytest.raises(TokenError):
        decode_token(create_refresh_token(7), ACCESS_TOKEN_TYPE)


def test_garbage_token_is_rejected():
    with pytest.raises(TokenError):
        decode_token("not-a-jwt", ACCESS_TOKEN_TYPE)
