import pytest

from tests.conftest import PASSWORD, token_for


def register(client, **overrides):
    body = {"username": "alice", "email": "Alice@Example.com", "password": PASSWORD} | overrides
    return client.post("/api/v1/users", json=body)


def test_register_returns_public_profile(client):
    res = register(client)
    assert res.status_code == 201
    body = res.json()
    assert body["username"] == "alice"
    assert body["email"] == "alice@example.com"
    assert "password" not in body and "hashed_password" not in body


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("username", "a"),
        ("username", "has space"),
        ("email", "not-an-email"),
        ("password", "short1"),
        ("password", "lettersonly"),
        ("password", "x1" * 40),  # > 72 bytes
    ],
)
def test_register_validation(client, field, value):
    res = register(client, **{field: value})
    assert res.status_code == 422
    assert res.json()["detail"][0]["loc"][-1] == field


def test_duplicate_username_and_email_conflict(client):
    assert register(client).status_code == 201
    assert register(client, email="other@example.com").status_code == 409
    res = register(client, username="ALICE2", email="ALICE@example.com")
    assert res.status_code == 409
    assert "email" in res.json()["detail"]


def test_username_is_case_insensitive_for_uniqueness(client):
    assert register(client).status_code == 201
    assert register(client, username="Alice", email="b@example.com").status_code == 409


def test_login_and_me(client, make_user):
    make_user("alice")
    headers = token_for(client, "alice")
    me = client.get("/api/v1/users/me", headers=headers)
    assert me.status_code == 200
    assert me.json()["username"] == "alice"


def test_login_failures(client, make_user):
    make_user("alice")
    for username, password in [("alice", "wrong-pass1"), ("nobody", PASSWORD)]:
        res = client.post("/api/v1/auth/token", data={"username": username, "password": password})
        assert res.status_code == 401
        assert res.headers["www-authenticate"] == "Bearer"


def test_inactive_user_cannot_log_in(client, make_user, db):
    user = make_user("alice")
    user.is_active = False
    db.commit()
    res = client.post("/api/v1/auth/token", data={"username": "alice", "password": PASSWORD})
    assert res.status_code == 401


def test_me_requires_a_valid_token(client):
    assert client.get("/api/v1/users/me").status_code == 401
    bad = {"Authorization": "Bearer not-a-jwt"}
    assert client.get("/api/v1/users/me", headers=bad).status_code == 401
