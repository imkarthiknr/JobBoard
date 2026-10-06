# Contributing

Thanks for taking the time to contribute!

## Reporting issues

Open an [issue](https://github.com/imkarthiknr/JobBoard/issues) with what you expected, what happened, steps to reproduce, and your OS, Python version and database (SQLite or PostgreSQL).

Please report security problems privately to the maintainer rather than in a public issue.

## Making changes

1. Fork the repo and branch from `main`: `git checkout -b feat/short-description`.
2. Set up the project with [DEVELOPMENT.md](DEVELOPMENT.md).
3. Make your change **with tests**. If you change a model, add an Alembic migration.
4. Check everything locally:

   ```bash
   uv run ruff check . && uv run ruff format --check .
   uv run pytest
   uv run alembic check
   ```

5. Commit using [Conventional Commits](https://www.conventionalcommits.org/), e.g. `feat(jobs): add salary range`.
6. Open a pull request explaining **what** and **why**. Include screenshots for UI changes.

## Guidelines

- Business rules belong in `app/services/`, not in route handlers.
- Keep the API and the web UI consistent. Both should go through the same service functions.
- Never commit secrets, `.env` files or virtual environments.
