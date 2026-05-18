# Contributing to Skillify

Thanks for your interest in contributing! Here's how to get started.

## Development Setup

```bash
git clone https://github.com/nickommen/skillify.git
cd skillify
uv venv .venv && source .venv/bin/activate
uv sync
```

## Running Tests

```bash
uv run pytest --cov
```

## Linting

```bash
uv run ruff check scripts/ tests/
```

## Submitting Changes

1. Fork the repo and create a branch from `main`.
2. Make your changes — add tests for new functionality.
3. Ensure `pytest` and `ruff check` pass.
4. Use [conventional commit](https://www.conventionalcommits.org/) format for your PR title (e.g. `feat: add X`, `fix: resolve Y`).
5. Open a pull request against `main`.

## Code Style

- Python 3.12+, stdlib-only for runtime code (dev dependencies like pytest/ruff are fine).
- Follow existing patterns in the codebase.
- Ruff handles formatting and linting — run it before submitting.

## Reporting Issues

Open an issue on GitHub. Include:
- What you expected to happen
- What actually happened
- Steps to reproduce
- Your Python version and OS

## License

By contributing, you agree that your contributions will be licensed under the MIT License.
