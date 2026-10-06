# Contributing to RivalScope

Thank you for your interest in contributing to RivalScope! We welcome bug reports, feature enhancements, documentation improvements, and pull requests.

## Development Setup

1. **Prerequisites**:
   - Python 3.12+
   - `uv` package manager (`curl -LsSf https://astral.sh/uv/install.sh | sh`)
   - Node.js 20+ and `pnpm`
   - Docker and Docker Compose (PostgreSQL 16 with pgvector + Redis)

2. **Clone and Configure**:
   ```bash
   git clone https://github.com/rivalscope/rivalscope.git
   cd rivalscope
   cp .env.example .env
   ```

3. **Start Core Infrastructure**:
   ```bash
   make up
   ```

4. **Install Backend Dependencies**:
   ```bash
   cd backend
   uv sync
   ```

5. **Run Migrations & Seed Demo Data**:
   ```bash
   make migrate
   make seed
   ```

6. **Run Quality Checks & Tests**:
   ```bash
   make lint
   make typecheck
   make test
   ```

## Pull Request Guidelines

- Ensure `ruff check`, `mypy`, and `pytest` pass before opening a PR.
- Maintain test coverage (>80% required on core modules).
- Document any architectural decisions in `docs/adr/`.
- Keep commits focused and atomic.
