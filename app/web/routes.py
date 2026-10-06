"""Server-rendered web UI (Jinja2). Uses the same services as the REST API.

Auth for the UI is the same JWT, stored in an HttpOnly, SameSite=Lax cookie. SameSite=Lax
means browsers don't send the cookie on cross-site POSTs, which protects the forms below
from CSRF without needing separate tokens.
"""

from pathlib import Path
from typing import Annotated
from urllib.parse import quote, unquote, urlencode

from fastapi import APIRouter, Form, HTTPException, Query, Request, status
from fastapi.responses import HTMLResponse, RedirectResponse, Response
from fastapi.templating import Jinja2Templates
from pydantic import ValidationError

from app.api.deps import AUTH_COOKIE, DbSession, OptionalUser
from app.core.config import get_settings
from app.core.security import create_access_token
from app.models import Job, User
from app.schemas.job import JobCreate
from app.schemas.user import UserCreate
from app.services import jobs as job_service
from app.services import users as user_service

templates = Jinja2Templates(directory=Path(__file__).parent / "templates")
router = APIRouter(include_in_schema=False)

FLASH_COOKIE = "flash"
PAGE_SIZE = 8


# ---------- helpers ----------


def render(request: Request, name: str, user: User | None, status_code: int = 200, **ctx):
    flash = request.cookies.get(FLASH_COOKIE)
    response = templates.TemplateResponse(
        request,
        name,
        {"user": user, "flash": unquote(flash) if flash else None, **ctx},
        status_code=status_code,
    )
    if flash:
        response.delete_cookie(FLASH_COOKIE)
    return response


def redirect(url: str, flash: str | None = None) -> RedirectResponse:
    response = RedirectResponse(url, status_code=status.HTTP_303_SEE_OTHER)
    if flash:
        response.set_cookie(FLASH_COOKIE, quote(flash), max_age=30, httponly=True, samesite="lax")
    return response


def login_redirect(request: Request) -> RedirectResponse:
    return redirect(f"/login?next={quote(request.url.path)}", "Please log in first.")


def safe_next(next_url: str | None) -> str:
    """Only allow local redirects after login (prevents open redirects)."""
    if next_url and next_url.startswith("/") and not next_url.startswith("//"):
        return next_url
    return "/"


def _friendly(err: dict) -> str:
    """Turn a Pydantic error into a sentence suitable for a form."""
    kind, ctx = err["type"], err.get("ctx") or {}
    if kind == "string_too_short":
        if not err.get("input"):
            return "This field is required."
        return f"Must be at least {ctx.get('min_length')} characters."
    if kind == "string_too_long":
        return f"Must be at most {ctx.get('max_length')} characters."
    if kind.startswith("url_"):
        return "Enter a full URL, e.g. https://example.com."
    if kind == "string_pattern_mismatch":
        return "Use only letters, numbers, dots, dashes and underscores."
    if kind == "value_error" and err["loc"] and err["loc"][0] == "email":
        return "Enter a valid email address."
    message = str(err["msg"]).removeprefix("Value error, ")
    return message[0].upper() + message[1:] + ("" if message.endswith(".") else ".")


def field_errors(exc: ValidationError) -> dict[str, str]:
    errors: dict[str, str] = {}
    for err in exc.errors():
        field = str(err["loc"][0]) if err["loc"] else "form"
        errors.setdefault(field, _friendly(dict(err)))
    return errors


def get_job_or_404(db: DbSession, job_id: int, user: User | None) -> Job:
    job = job_service.get_job(db, job_id)
    if job is None or (not job.is_active and not job_service.can_edit(user, job)):
        raise HTTPException(status.HTTP_404_NOT_FOUND)
    return job


def with_auth_cookie(response: Response, user: User) -> Response:
    settings = get_settings()
    response.set_cookie(
        AUTH_COOKIE,
        create_access_token(user.username),
        max_age=settings.access_token_expire_minutes * 60,
        httponly=True,
        samesite="lax",
        secure=settings.cookie_secure,
    )
    return response


# ---------- browse ----------


@router.get("/", response_class=HTMLResponse)
def home(
    request: Request,
    db: DbSession,
    user: OptionalUser,
    q: Annotated[str, Query(max_length=100)] = "",
    location: Annotated[str, Query(max_length=100)] = "",
    page: Annotated[int, Query(ge=1)] = 1,
):
    result = job_service.search_jobs(db, q=q, location=location, page=page, size=PAGE_SIZE)

    def page_url(n: int) -> str:
        params = {k: v for k, v in {"q": q, "location": location}.items() if v}
        if n > 1:
            params["page"] = str(n)
        return "/?" + urlencode(params) if params else "/"

    return render(
        request, "jobs/list.html", user, result=result, q=q, location=location, page_url=page_url
    )


@router.get("/jobs/{job_id}", response_class=HTMLResponse)
def job_detail(job_id: int, request: Request, db: DbSession, user: OptionalUser):
    job = get_job_or_404(db, job_id, user)
    return render(
        request, "jobs/detail.html", user, job=job, can_edit=job_service.can_edit(user, job)
    )


# ---------- post & manage jobs ----------


@router.get("/post-job", response_class=HTMLResponse)
def new_job_form(request: Request, user: OptionalUser):
    if user is None:
        return login_redirect(request)
    return render(request, "jobs/form.html", user, values={}, errors={})


@router.post("/post-job", response_class=HTMLResponse)
def create_job(
    request: Request,
    db: DbSession,
    user: OptionalUser,
    title: Annotated[str, Form()] = "",
    company: Annotated[str, Form()] = "",
    company_url: Annotated[str, Form()] = "",
    location: Annotated[str, Form()] = "",
    description: Annotated[str, Form()] = "",
):
    if user is None:
        return login_redirect(request)
    values = {
        "title": title,
        "company": company,
        "company_url": company_url,
        "location": location,
        "description": description,
    }
    try:
        data = JobCreate.model_validate({**values, "company_url": company_url.strip() or None})
    except ValidationError as exc:
        return render(
            request,
            "jobs/form.html",
            user,
            values=values,
            errors=field_errors(exc),
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
        )
    job = job_service.create_job(db, data, owner=user)
    return redirect(f"/jobs/{job.id}", "Your job is live.")


@router.get("/my-jobs", response_class=HTMLResponse)
def my_jobs(request: Request, db: DbSession, user: OptionalUser):
    if user is None:
        return login_redirect(request)
    return render(request, "jobs/mine.html", user, jobs=job_service.list_owned_by(db, user))


@router.post("/jobs/{job_id}/toggle")
def toggle_job(job_id: int, request: Request, db: DbSession, user: OptionalUser):
    if user is None:
        return login_redirect(request)
    job = get_job_or_404(db, job_id, user)
    if not job_service.can_edit(user, job):
        raise HTTPException(status.HTTP_403_FORBIDDEN)
    job.is_active = not job.is_active
    db.commit()
    return redirect(
        f"/jobs/{job.id}", "Job reopened." if job.is_active else "Job closed to new applicants."
    )


@router.post("/jobs/{job_id}/delete")
def delete_job(job_id: int, request: Request, db: DbSession, user: OptionalUser):
    if user is None:
        return login_redirect(request)
    job = get_job_or_404(db, job_id, user)
    if not job_service.can_edit(user, job):
        raise HTTPException(status.HTTP_403_FORBIDDEN)
    job_service.delete_job(db, job)
    return redirect("/my-jobs", "Job deleted.")


# ---------- auth ----------


@router.get("/register", response_class=HTMLResponse)
def register_form(request: Request, user: OptionalUser):
    return render(request, "auth/register.html", user, values={}, errors={})


@router.post("/register", response_class=HTMLResponse)
def register(
    request: Request,
    db: DbSession,
    user: OptionalUser,
    username: Annotated[str, Form()] = "",
    email: Annotated[str, Form()] = "",
    password: Annotated[str, Form()] = "",
):
    values = {"username": username.strip(), "email": email.strip()}
    try:
        data = UserCreate.model_validate({**values, "password": password})
        new_user = user_service.create_user(db, data)
    except ValidationError as exc:
        errors = field_errors(exc)
    except user_service.DuplicateUserError as exc:
        errors = {exc.field: f"This {exc.field} is already taken."}
    else:
        return with_auth_cookie(redirect("/", f"Welcome, {new_user.username}!"), new_user)
    return render(
        request,
        "auth/register.html",
        user,
        values=values,
        errors=errors,
        status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
    )


@router.get("/login", response_class=HTMLResponse)
def login_form(request: Request, user: OptionalUser, next: str = "/"):
    return render(request, "auth/login.html", user, next=safe_next(next), error=None, username="")


@router.post("/login", response_class=HTMLResponse)
def login(
    request: Request,
    db: DbSession,
    username: Annotated[str, Form()] = "",
    password: Annotated[str, Form()] = "",
    next: Annotated[str, Form()] = "/",
):
    user = user_service.authenticate(db, username.strip(), password)
    if user is None:
        return render(
            request,
            "auth/login.html",
            None,
            next=safe_next(next),
            error="Incorrect username or password.",
            username=username,
            status_code=status.HTTP_401_UNAUTHORIZED,
        )
    return with_auth_cookie(redirect(safe_next(next), f"Logged in as {user.username}."), user)


@router.post("/logout")
def logout():
    response = redirect("/", "You have been logged out.")
    response.delete_cookie(AUTH_COOKIE)
    return response
