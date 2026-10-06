from typing import Annotated

from fastapi import APIRouter, HTTPException, Query, Response, status

from app.api.deps import CurrentUser, DbSession, OptionalUser
from app.models import Job
from app.schemas.job import JobCreate, JobPage, JobRead, JobUpdate
from app.services import jobs as job_service

router = APIRouter(prefix="/jobs", tags=["jobs"])


def _get_or_404(db: DbSession, job_id: int) -> Job:
    job = job_service.get_job(db, job_id)
    if job is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Job not found")
    return job


def _get_editable(db: DbSession, job_id: int, user: CurrentUser) -> Job:
    job = _get_or_404(db, job_id)
    if not job_service.can_edit(user, job):
        raise HTTPException(status.HTTP_403_FORBIDDEN, detail="You can only change your own jobs")
    return job


@router.get("", response_model=JobPage)
def list_jobs(
    db: DbSession,
    q: Annotated[
        str, Query(max_length=100, description="Matches title, company, description")
    ] = "",
    location: Annotated[str, Query(max_length=100)] = "",
    page: Annotated[int, Query(ge=1)] = 1,
    size: Annotated[int, Query(ge=1, le=50)] = 10,
) -> JobPage:
    """Search active jobs, newest first."""
    result = job_service.search_jobs(db, q=q, location=location, page=page, size=size)
    return JobPage(
        items=[JobRead.model_validate(j) for j in result.items],
        total=result.total,
        page=result.page,
        size=result.size,
        pages=result.pages,
    )


@router.get("/{job_id}", response_model=JobRead)
def read_job(job_id: int, db: DbSession, user: OptionalUser) -> JobRead:
    job = _get_or_404(db, job_id)
    # Inactive postings are only visible to the people who can edit them.
    if not job.is_active and not job_service.can_edit(user, job):
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Job not found")
    return JobRead.model_validate(job)


@router.post("", response_model=JobRead, status_code=status.HTTP_201_CREATED)
def create_job(data: JobCreate, db: DbSession, user: CurrentUser, response: Response) -> JobRead:
    job = job_service.create_job(db, data, owner=user)
    response.headers["Location"] = f"/api/v1/jobs/{job.id}"
    return JobRead.model_validate(job)


@router.patch("/{job_id}", response_model=JobRead)
def update_job(job_id: int, data: JobUpdate, db: DbSession, user: CurrentUser) -> JobRead:
    job = _get_editable(db, job_id, user)
    return JobRead.model_validate(job_service.update_job(db, job, data))


@router.delete("/{job_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_job(job_id: int, db: DbSession, user: CurrentUser) -> None:
    job_service.delete_job(db, _get_editable(db, job_id, user))
