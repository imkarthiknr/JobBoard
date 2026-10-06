"""Job queries and mutations. No HTTP concerns here."""

import math
from dataclasses import dataclass

from sqlalchemy import Select, func, or_, select
from sqlalchemy.orm import Session

from app.models import Job, User
from app.schemas.job import JobCreate, JobUpdate


@dataclass(frozen=True)
class JobSearchResult:
    items: list[Job]
    total: int
    page: int
    size: int

    @property
    def pages(self) -> int:
        return max(1, math.ceil(self.total / self.size))


def _escape_like(term: str) -> str:
    return term.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")


def _search_query(q: str, location: str, include_inactive: bool) -> Select[tuple[Job]]:
    stmt = select(Job)
    if not include_inactive:
        stmt = stmt.where(Job.is_active.is_(True))
    if q:
        pattern = f"%{_escape_like(q)}%"
        stmt = stmt.where(
            or_(
                Job.title.ilike(pattern, escape="\\"),
                Job.company.ilike(pattern, escape="\\"),
                Job.description.ilike(pattern, escape="\\"),
            )
        )
    if location:
        stmt = stmt.where(Job.location.ilike(f"%{_escape_like(location)}%", escape="\\"))
    return stmt


def search_jobs(
    db: Session,
    *,
    q: str = "",
    location: str = "",
    page: int = 1,
    size: int = 10,
    include_inactive: bool = False,
) -> JobSearchResult:
    """Full-text-ish search over title, company and description; newest first."""
    base = _search_query(q.strip(), location.strip(), include_inactive)
    total = db.scalar(select(func.count()).select_from(base.subquery())) or 0
    items = db.scalars(
        base.order_by(Job.date_posted.desc(), Job.id.desc()).offset((page - 1) * size).limit(size)
    ).all()
    return JobSearchResult(items=list(items), total=total, page=page, size=size)


def list_owned_by(db: Session, owner: User) -> list[Job]:
    stmt = select(Job).where(Job.owner_id == owner.id).order_by(Job.id.desc())
    return list(db.scalars(stmt).all())


def get_job(db: Session, job_id: int) -> Job | None:
    return db.get(Job, job_id)


def create_job(db: Session, data: JobCreate, owner: User) -> Job:
    job = Job(
        **data.model_dump(exclude={"company_url"}),
        company_url=str(data.company_url) if data.company_url else None,
        owner_id=owner.id,
    )
    db.add(job)
    db.commit()
    db.refresh(job)
    return job


def update_job(db: Session, job: Job, data: JobUpdate) -> Job:
    changes = data.model_dump(exclude_unset=True)
    if "company_url" in changes:
        changes["company_url"] = str(data.company_url) if data.company_url else None
    for field, value in changes.items():
        if value is None and field != "company_url":
            continue  # required columns can't be cleared
        setattr(job, field, value)
    db.commit()
    db.refresh(job)
    return job


def delete_job(db: Session, job: Job) -> None:
    db.delete(job)
    db.commit()


def can_edit(user: User | None, job: Job) -> bool:
    return user is not None and (user.is_superuser or job.owner_id == user.id)
