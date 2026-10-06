from app.core.security import (
    create_access_token,
    decode_access_token,
    hash_password,
    verify_password,
)


def test_hash_and_verify():
    hashed = hash_password("correct-horse1")
    assert hashed.startswith("$2b$")
    assert "correct-horse1" not in hashed
    assert verify_password("correct-horse1", hashed)
    assert not verify_password("wrong-horse1", hashed)


def test_verify_rejects_malformed_hash():
    assert not verify_password("anything", "not-a-bcrypt-hash")


def test_token_round_trip():
    assert decode_access_token(create_access_token("alice")) == "alice"


def test_expired_and_tampered_tokens_are_rejected():
    assert decode_access_token(create_access_token("alice", expires_minutes=-1)) is None
    token = create_access_token("alice")
    assert decode_access_token(token[:-2] + ("AA" if token[-2:] != "AA" else "BB")) is None
    assert decode_access_token("garbage") is None
