<!-- OPENSPEC:START -->
# OpenSpec Instructions

These instructions are for AI assistants working in this project.

Always open `@/openspec/AGENTS.md` when the request:
- Mentions planning or proposals (words like proposal, spec, change, plan)
- Introduces new capabilities, breaking changes, architecture shifts, or big performance/security work
- Sounds ambiguous and you need the authoritative spec before coding

Use `@/openspec/AGENTS.md` to learn:
- How to create and apply change proposals
- Spec format and conventions
- Project structure and guidelines

Keep this managed block so 'openspec update' can refresh the instructions.

<!-- OPENSPEC:END -->

# Development Guide

## Build & Test Commands

```bash
# Dependencies
make install                    # Install all dependencies
uv sync --dev                  # Sync dev dependencies

# Lint & Format
make lint                      # Run ruff + mypy
make fix-lint                  # Auto-fix with ruff, black, isort
make format                    # Format with black + isort

# Testing
make test                      # Run unit tests (excludes e2e)
uv run pytest tests/unit       # Run unit tests only
uv run pytest tests/unit/test_gmail_tools.py::TestGmailTools::test_query_gmail_emails_success  # Run single test
make coverage                  # Run with coverage report

# E2E Tests (requires credentials)
make e2e-tests                 # Run all E2E tests
dotenvx run -f .env.local -- uv run pytest tests/e2e/test_gmail_api.py -v  # Single E2E test file
```

## Code Style Guidelines

**Imports**: Standard library → third-party → local modules (ruff + isort enforce this)
```python
import json
import logging
from typing import Annotated

from fastmcp import Context
from mcp.types import TextContent

from . import auth_helper
from .common import get_user_id_description
```

**Formatting**: 
- Line length: 120 chars
- Quote style: double quotes
- Python 3.13 syntax (requires-python >= 3.13)

**Type Hints**:
- Use `Annotated[type, "description"]` for function parameters
- Use `str | None` instead of `Optional[str]` (PEP 604)
- Use `list[T]` instead of `List[T]` (built-in generics)

**Naming**:
- Functions/variables: `snake_case`
- Classes: `PascalCase`
- Constants: `UPPER_SNAKE_CASE`
- Private: prefix with `_`

**Error Handling**:
```python
try:
    # operation
except Exception as e:
    logger.error(f"Error in function_name: {e}", exc_info=True)
    error_msg = f"Error message: {e}"
    if ctx:
        await ctx.error(error_msg)
    raise RuntimeError(error_msg) from e
```

**Testing**:
- Unit tests use `unittest.TestCase` and mocks
- E2E tests marked with `@pytest.mark.e2e` 
- Async tests require `pytest-asyncio`
- Mock external services (Gmail, Calendar APIs)