from datetime import date, timedelta

from app.models import Job
from tests.conftest import JOB, token_for

API = "/api/v1/jobs"


def post_job(client, headers, **overrides):
    return client.post(API, json=JOB | overrides, headers=headers)


def test_creating_a_job_requires_auth(client):
    assert client.post(API, json=JOB).status_code == 401


def test_create_and_read(client, make_user):
    alice = make_user("alice")
    res = post_job(client, token_for(client, "alice"))
    assert res.status_code == 201
    job = res.json()
    assert res.headers["location"] == f"/api/v1/jobs/{job['id']}"
    assert job["owner_id"] == alice.id
    assert job["date_posted"] == date.today().isoformat()
    assert job["is_active"] is True
    assert client.get(f"{API}/{job['id']}").json()["title"] == "Backend Engineer"


def test_create_validation(client, make_user):
    make_user("alice")
    headers = token_for(client, "alice")
    res = post_job(client, headers, title="", company_url="not a url", description="short")
    assert res.status_code == 422
    fields = {e["loc"][-1] for e in res.json()["detail"]}
    assert fields == {"title", "company_url", "description"}


def test_list_search_filters_and_paginates(client, db, make_user):
    owner = make_user("alice")
    today = date.today()
    for i, (title, location) in enumerate(
        [
            ("Python Developer", "Chennai"),
            ("Angular Developer", "Berlin"),
            ("Data Engineer (Python)", "Remote"),
            ("Old Python Role", "Chennai"),
        ]
    ):
        db.add(
            Job(
                title=title,
                company="Acme",
                location=location,
                description="Some description here.",
                date_posted=today - timedelta(days=i),
                owner_id=owner.id,
            )
        )
    db.add(
        Job(
            title="Closed Python Role",
            company="Acme",
            location="Chennai",
            description="No longer hiring.",
            is_active=False,
            owner_id=owner.id,
        )
    )
    db.commit()

    everything = client.get(API).json()
    assert everything["total"] == 4  # inactive excluded
    assert everything["items"][0]["title"] == "Python Developer"  # newest first

    python = client.get(API, params={"q": "python"}).json()
    assert [j["title"] for j in python["items"]] == [
        "Python Developer",
        "Data Engineer (Python)",
        "Old Python Role",
    ]

    chennai_python = client.get(API, params={"q": "PYTHON", "location": "chen"}).json()
    assert chennai_python["total"] == 2

    page2 = client.get(API, params={"size": 3, "page": 2}).json()
    assert (page2["total"], page2["pages"], len(page2["items"])) == (4, 2, 1)


def test_search_treats_wildcards_literally(client, make_user):
    make_user("alice")
    post_job(client, token_for(client, "alice"))
    assert client.get(API, params={"q": "%"}).json()["total"] == 0
    assert client.get(API, params={"q": "_"}).json()["total"] == 0


def test_list_parameter_validation(client):
    assert client.get(API, params={"page": 0}).status_code == 422
    assert client.get(API, params={"size": 51}).status_code == 422


def test_owner_can_update_and_delete(client, make_user):
    make_user("alice")
    headers = token_for(client, "alice")
    job_id = post_job(client, headers).json()["id"]

    res = client.patch(f"{API}/{job_id}", json={"title": "Staff Engineer"}, headers=headers)
    assert res.status_code == 200
    assert res.json()["title"] == "Staff Engineer"
    assert res.json()["company"] == "Kaveri Labs"  # untouched

    assert client.delete(f"{API}/{job_id}", headers=headers).status_code == 204
    assert client.get(f"{API}/{job_id}").status_code == 404


def test_other_users_cannot_modify(client, make_user):
    make_user("alice")
    make_user("bob")
    job_id = post_job(client, token_for(client, "alice")).json()["id"]
    bob = token_for(client, "bob")
    assert client.patch(f"{API}/{job_id}", json={"title": "Hacked"}, headers=bob).status_code == 403
    assert client.delete(f"{API}/{job_id}", headers=bob).status_code == 403


def test_superuser_can_moderate(client, make_user):
    make_user("alice")
    make_user("admin", superuser=True)
    job_id = post_job(client, token_for(client, "alice")).json()["id"]
    assert client.delete(f"{API}/{job_id}", headers=token_for(client, "admin")).status_code == 204


def test_closed_jobs_are_hidden_from_everyone_but_the_owner(client, make_user):
    make_user("alice")
    make_user("bob")
    alice = token_for(client, "alice")
    job_id = post_job(client, alice).json()["id"]
    client.patch(f"{API}/{job_id}", json={"is_active": False}, headers=alice)

    assert client.get(f"{API}/{job_id}").status_code == 404
    assert client.get(f"{API}/{job_id}", headers=token_for(client, "bob")).status_code == 404
    assert client.get(f"{API}/{job_id}", headers=alice).status_code == 200
    mine = client.get("/api/v1/users/me/jobs", headers=alice).json()
    assert [j["is_active"] for j in mine] == [False]


def test_unknown_job_is_404(client):
    assert client.get(f"{API}/999").status_code == 404
    assert client.get(f"{API}/not-a-number").status_code == 422


def test_deleting_a_user_cascades_to_jobs(client, db, make_user):
    alice = make_user("alice")
    post_job(client, token_for(client, "alice"))
    db.delete(alice)
    db.commit()
    assert client.get(API).json()["total"] == 0
