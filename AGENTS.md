# Repository Guidelines

## Project Structure & Module Organization
- `main.sh` is the single launcher; run `./main.sh api|worker|beat` to start the FastAPI API, Celery worker, or Celery beat.
- Feature modules live in `features/<name>/` with `domain/`, `application/`, `infrastructure/`, and `interface/` subpackages (see `features/proxy_pool` for the template); keep new code in the matching layer.
- Place reusable scripts in `scripts/`, runtime data in `data.db`, and ensure all tests remain in `tests/` with paths mirroring the feature they cover (e.g., `tests/proxy_pool/test_healthcheck.py`).

## Build, Test, and Development Commands
- `python -m venv .venv && source .venv/bin/activate`: prepare a CentOS-compatible virtual environment.
- `pip install -e .`: install dependencies from `pyproject.toml` for editable development.
- `./main.sh api` (or `worker`/`beat`): run the selected service using exported env vars such as `APP_PORT=8000`.
- `pytest` or `pytest tests/proxy_pool -k health`: execute the full or targeted suite; always run before sending changes.
- `docker compose up -d --build`: rebuild and start the full stack (API, workers, Redis, glider) for integration checks.

## Coding Style & Naming Conventions
- Target Python 3.9+, four-space indentation, and class-oriented modules that follow SOLID responsibilities.
- Keep domain objects pure, application services orchestration-only, and infrastructure modules responsible for IO adapters; FastAPI routers stay within `interface/`.
- Use snake_case for functions, PascalCase for classes, and concise, feature-scoped filenames such as `glider_config_service.py`. Add type hints and short docstrings when logic is non-trivial.

## Testing Guidelines
- Write `pytest` tests named `test_<behavior>` inside files like `test_subscription_parser.py`; isolate fixtures per module.
- Prefer unit tests for domain/application layers; mock or fake external services when exercising infrastructure helpers.
- Maintain deterministic assertions and run `pytest` (optionally with `--maxfail=1`) before each commit or pull request.

## Commit & Pull Request Guidelines
- Use imperative, scoped subjects (e.g., `fix(proxy_pool): handle empty subscription`) and keep each commit focused on one concern.
- PRs should include a summary, linked issue, verification steps (command list), and screenshots or logs when altering runtime behavior.
- Update documentation (including this file or `docs/`) whenever public contracts, CLI arguments, or API endpoints change.

## Operations & Configuration Tips
- Keep environment defaults in `.env` aligned with `docker-compose.yml`; document new variables within the PR description.
- Ensure `glider/glider` remains executable (`chmod +x glider/glider`) and store custom subscription sources in `subscriptions.txt` for collectors to consume.
