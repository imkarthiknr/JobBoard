# Changelog

All notable changes to this project are documented here.
The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and the project follows [Semantic Versioning](https://semver.org/).

## [1.0.0] - 2026-10-06

The 2022 groundwork was completed into a working, tested and containerised job board.

### Added

- REST API under `/api/v1`: registration, OAuth2 password login with JWT, `users/me`, job search (keyword, location, pagination), and create/update/delete with ownership rules and superuser moderation.
- Server-rendered web UI (Jinja2): browse and search, job details, sign up/log in/log out, post a job, close/reopen/delete, "My jobs", flash messages, and HTML error pages.
- Service layer shared by the API and the UI.
- Alembic migrations, a demo-data seed script and a `/health` endpoint.
- Dockerfile (non-root, health check) and Docker Compose with PostgreSQL 16.
- 46 pytest tests that run on both SQLite and PostgreSQL, plus a migration-drift check.
- GitHub Actions CI: ruff, tests (Python 3.11/3.13, SQLite + PostgreSQL), and a Docker Compose smoke test.
- README, DEVELOPMENT guide, API examples, CONTRIBUTING, MIT license, screenshots.

### Changed

- Restructured from `backend/` with top-level module imports into an `app/` package.
- SQLAlchemy 1.4 declarative models upgraded to typed SQLAlchemy 2.0 models. Tables renamed `user`/`job` → `users`/`jobs`.
- `psycopg2` → `psycopg` 3. `passlib` → `bcrypt` (passlib is unmaintained and incompatible with current bcrypt).
- Hand-rolled `Settings` class replaced with `pydantic-settings`. SQLite is now the zero-setup default.
- Dependencies are declared in `pyproject.toml` and locked with `uv.lock`, replacing an unpinned `requirements.txt`.

### Removed

- The committed Windows virtualenv (`backend/env/`), `__pycache__` files and the committed `backend/.env`. They are now gitignored; `.env.example` documents the settings.
- Stray imports (`from turtle import st`, `from re import S`) in the user schema.

### Security

- `backend/.env` containing a local database password was committed in earlier revisions. It is removed from the current tree, but **remains in git history**. Treat that password as compromised and rotate it if it is used anywhere.

## [0.1.1] - 2022-04-11

### Added

- `User` and `Job` SQLAlchemy models, a bcrypt `Hasher` helper and a `UserCreate` schema.

## [0.1.0] - 2022-04-03 – 2022-04-06

### Added

- FastAPI skeleton with a PostgreSQL connection configured from `.env`.

[1.0.0]: https://github.com/imkarthiknr/JobBoard/compare/38710cf...main
[0.1.1]: https://github.com/imkarthiknr/JobBoard/commit/38710cf
[0.1.0]: https://github.com/imkarthiknr/JobBoard/commit/b7b74a4
