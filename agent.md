# Project Guidelines: RSOS Meal Planner

This project uses **uv** for Python package management and project orchestration.

## General Rules
- Always use `uv run ...` to execute commands (e.g., `uv run python manage.py migrate`).
- Do not use `pip` or standard `python` commands directly without `uv run` unless working inside an already activated virtual environment.
- Use `uv add <package>` to add new dependencies.
- Ensure `uv.lock` is updated whenever `pyproject.toml` changes.
