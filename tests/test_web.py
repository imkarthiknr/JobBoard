"""Server-rendered UI: pages render, forms work, and ownership rules hold."""

import pytest

from tests.conftest import JOB, PASSWORD, token_for


def login(client, username="alice", password=PASSWORD, next_url="/"):
    return client.post(
        "/login",
        data={"username": username, "password": password, "next": next_url},
        follow_redirects=False,
    )


def create_via_api(client, username="alice", **overrides):
    res = client.post("/api/v1/jobs", json=JOB | overrides, headers=token_for(client, username))
    return res.json()["id"]


def test_home_lists_and_searches_jobs(client, make_user):
    make_user("alice")
    create_via_api(client, title="Python Developer")
    create_via_api(client, title="Angular Developer", location="Berlin")

    page = client.get("/")
    assert page.status_code == 200
    assert "Python Developer" in page.text and "Angular Developer" in page.text
    assert "2 jobs" in page.text

    search = client.get("/", params={"q": "angular"})
    assert "Angular Developer" in search.text and "Python Developer" not in search.text
    assert 'value="angular"' in search.text


def test_empty_state(client):
    assert "No jobs found" in client.get("/").text


def test_job_detail_escapes_html(client, make_user):
    make_user("alice")
    job_id = create_via_api(client, description="<script>alert(1)</script> and more text")
    page = client.get(f"/jobs/{job_id}")
    assert page.status_code == 200
    assert "<script>alert(1)</script>" not in page.text
    assert "&lt;script&gt;" in page.text


def test_unknown_job_renders_html_404(client):
    page = client.get("/jobs/12345")
    assert page.status_code == 404
    assert "text/html" in page.headers["content-type"]
    assert "Page not found" in page.text


def test_post_job_requires_login(client):
    for res in (
        client.get("/post-job", follow_redirects=False),
        client.get("/my-jobs", follow_redirects=False),
    ):
        assert res.status_code == 303
        assert res.headers["location"].startswith("/login?next=/")


def test_register_logs_in_and_redirects(client):
    res = client.post(
        "/register",
        data={"username": "carol", "email": "carol@example.com", "password": PASSWORD},
        follow_redirects=False,
    )
    assert res.status_code == 303
    assert "access_token" in res.cookies
    home = client.get("/")
    assert "Welcome, carol!" in home.text  # flash message
    assert "Log out" in home.text
    assert "Welcome, carol!" not in client.get("/").text  # flash shown once


def test_register_shows_errors(client, make_user):
    make_user("alice")
    res = client.post(
        "/register", data={"username": "alice", "email": "new@example.com", "password": PASSWORD}
    )
    assert res.status_code == 422
    assert "This username is already taken." in res.text
    res = client.post("/register", data={"username": "dave", "email": "bad", "password": "short"})
    assert res.status_code == 422
    assert 'value="dave"' in res.text  # input preserved


def test_login_success_failure_and_logout(client, make_user):
    make_user("alice")
    bad = login(client, password="wrong-pass1")
    assert bad.status_code == 401
    assert "Incorrect username or password." in bad.text

    ok = login(client, next_url="/my-jobs")
    assert ok.status_code == 303
    assert ok.headers["location"] == "/my-jobs"
    cookie = ok.headers["set-cookie"].lower()
    assert "httponly" in cookie and "samesite=lax" in cookie

    out = client.post("/logout", follow_redirects=False)
    assert out.status_code == 303
    assert "Log in" in client.get("/").text


@pytest.mark.parametrize(
    "target", ["https://evil.example.com", "//evil.example.com", "javascript:x"]
)
def test_login_never_redirects_off_site(client, make_user, target):
    make_user("alice")
    assert login(client, next_url=target).headers["location"] == "/"


def test_post_job_via_form(client, make_user):
    make_user("alice")
    login(client)

    invalid = client.post("/post-job", data={"title": "", "company": "Acme", "location": "X"})
    assert invalid.status_code == 422
    assert 'aria-invalid="true"' in invalid.text
    assert 'value="Acme"' in invalid.text

    res = client.post("/post-job", data=JOB, follow_redirects=False)
    assert res.status_code == 303
    detail = client.get(res.headers["location"])
    assert "Backend Engineer" in detail.text
    assert "Your job is live." in detail.text
    assert "Close posting" in detail.text  # owner controls visible


def test_owner_can_close_reopen_and_delete(client, make_user):
    make_user("alice")
    job_id = create_via_api(client)
    login(client)

    client.post(f"/jobs/{job_id}/toggle")
    assert "Backend Engineer" not in client.get("/").text  # closed jobs leave the board
    assert "Closed" in client.get("/my-jobs").text
    client.post(f"/jobs/{job_id}/toggle")
    assert "Backend Engineer" in client.get("/").text

    res = client.post(f"/jobs/{job_id}/delete", follow_redirects=False)
    assert res.headers["location"] == "/my-jobs"
    assert client.get(f"/jobs/{job_id}").status_code == 404


def test_non_owner_cannot_manage(client, make_user):
    make_user("alice")
    make_user("bob")
    job_id = create_via_api(client, "alice")
    login(client, "bob")
    assert "Close posting" not in client.get(f"/jobs/{job_id}").text
    assert client.post(f"/jobs/{job_id}/delete").status_code == 403
    assert client.post(f"/jobs/{job_id}/toggle").status_code == 403


def test_health_and_openapi(client):
    assert client.get("/health").json() == {"status": "ok"}
    paths = client.get("/openapi.json").json()["paths"]
    assert "/api/v1/jobs" in paths and "/" not in paths  # UI routes hidden from schema


def test_form_errors_are_human_friendly(client, make_user):
    make_user("alice")
    login(client)
    res = client.post(
        "/post-job",
        data={
            "title": "",
            "company": "Acme",
            "location": "Chennai",
            "company_url": "nope",
            "description": "short",
        },
    )
    assert "This field is required." in res.text
    assert "Enter a full URL" in res.text
    assert "Must be at least 10 characters." in res.text
    res = client.post("/register", data={"username": "bad name", "email": "x", "password": "abc"})
    assert "Use only letters, numbers" in res.text
    assert "Enter a valid email address." in res.text
    assert "Must be at least 8 characters." in res.text
