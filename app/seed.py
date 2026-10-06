"""Load demo users and jobs: `python -m app.seed`. Safe to run more than once."""

from datetime import date, timedelta

from app.db.session import SessionLocal
from app.models import Job
from app.schemas.user import UserCreate
from app.services import users as user_service

DEMO_PASSWORD = "jobboard123"

JOBS = [
    (
        "Senior Backend Engineer (Python)",
        "Kaveri Labs",
        "Chennai, India",
        0,
        "Design and run FastAPI services backed by PostgreSQL.\n\nYou'll own APIs end to end: "
        "schema design, observability and on-call.\n\nRequirements:\n- 5+ years Python\n"
        "- SQL and query tuning\n- Docker and CI/CD",
    ),
    (
        "Frontend Developer (Angular)",
        "Nordlicht GmbH",
        "Berlin, Germany",
        1,
        "Build accessible, fast UIs with Angular and TypeScript for our logistics platform.",
    ),
    (
        "Platform Engineer",
        "Hikari Systems",
        "Remote (APAC)",
        2,
        "Kubernetes, Terraform and developer tooling. Help 40 engineers ship safely every day.",
    ),
    (
        "Data Engineer",
        "Baobab Data",
        "Lagos, Nigeria",
        3,
        "Own batch and streaming pipelines (Airflow, Kafka) feeding our analytics warehouse.",
    ),
    (
        "Site Reliability Engineer",
        "Norrsken AB",
        "Stockholm, Sweden",
        4,
        "Define SLOs, improve incident response and automate toil across our AWS estate.",
    ),
    (
        "Full-Stack Engineer",
        "Tejo Digital",
        "Lisbon, Portugal",
        5,
        "Ship features across a Python API and a TypeScript front end for fintech clients.",
    ),
    (
        "Machine Learning Engineer",
        "Charminar Tech",
        "Hyderabad, India",
        6,
        "Productionise ranking models; build evaluation pipelines and feature stores.",
    ),
    (
        "QA Automation Engineer",
        "Mole Analytics",
        "Turin, Italy",
        7,
        "Grow our Playwright and pytest suites and make CI fast and trustworthy.",
    ),
    (
        "Engineering Manager",
        "Southern Cross IT",
        "Melbourne, Australia",
        9,
        "Lead a team of 7 building payments infrastructure. Hands-on architecture reviews.",
    ),
    (
        "Junior Python Developer",
        "Petra Works",
        "Remote (EMEA)",
        12,
        "Learn from senior engineers while building internal tools with FastAPI.",
    ),
]


def seed() -> None:
    with SessionLocal() as db:
        owner = user_service.get_by_username(db, "demo")
        if owner is None:
            owner = user_service.create_user(
                db, UserCreate(username="demo", email="demo@example.com", password=DEMO_PASSWORD)
            )
        if owner.jobs:
            print("Demo data already present; nothing to do.")
            return
        today = date.today()
        for title, company, location, days_ago, description in JOBS:
            db.add(
                Job(
                    title=title,
                    company=company,
                    company_url=None,
                    location=location,
                    description=description,
                    date_posted=today - timedelta(days=days_ago),
                    owner_id=owner.id,
                )
            )
        db.commit()
        print(f"Seeded {len(JOBS)} jobs. Log in as demo / {DEMO_PASSWORD}")


if __name__ == "__main__":
    seed()
