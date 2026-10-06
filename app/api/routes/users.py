from fastapi import APIRouter, HTTPException, status

from app.api.deps import CurrentUser, DbSession
from app.schemas.job import JobRead
from app.schemas.user import UserCreate, UserRead
from app.services import jobs as job_service
from app.services import users as user_service

router = APIRouter(prefix="/users", tags=["users"])


@router.post("", response_model=UserRead, status_code=status.HTTP_201_CREATED)
def register(data: UserCreate, db: DbSession) -> UserRead:
    try:
        user = user_service.create_user(db, data)
    except user_service.DuplicateUserError as exc:
        raise HTTPException(status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    return UserRead.model_validate(user)


@router.get("/me", response_model=UserRead)
def read_me(user: CurrentUser) -> UserRead:
    return UserRead.model_validate(user)


@router.get("/me/jobs", response_model=list[JobRead])
def read_my_jobs(user: CurrentUser, db: DbSession) -> list[JobRead]:
    """All of the current user's postings, including inactive ones."""
    return [JobRead.model_validate(j) for j in job_service.list_owned_by(db, user)]
