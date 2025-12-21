# Project Context

## Purpose

**fastmcp-gsuite** is an MCP (Model Context Protocol) server that enables AI assistants like Claude to interact with Google Workspace (G Suite) products. It provides tools for Gmail, Google Calendar, and Google Drive integration through the MCP protocol.

This project is a fork of [mcp-gsuite](https://github.com/MarkusPfundstein/mcp-gsuite), rewritten using the `fastmcp` library.

### Key Features
- Multiple Google account support
- Gmail: Query, read, draft, reply, and manage emails with attachments
- Calendar: View, create, and delete events across multiple calendars
- Drive: File operations and integration with Gmail attachments

## Tech Stack

- **Language**: Python 3.13+
- **Framework**: fastmcp 2.1.x (MCP server framework)
- **Configuration**: pydantic-settings
- **Google APIs**: google-api-python-client, oauth2client
- **Package Manager**: uv
- **Build System**: hatchling

### Key Dependencies
- `fastmcp>=2.1.2,<2.2.0` - MCP server framework
- `google-api-python-client>=2.154.0` - Google API client
- `pydantic-settings>=2.8.1,<2.9.0` - Settings management
- `beautifulsoup4>=4.12.3` - HTML parsing for emails

## Project Conventions

### Code Style
- **Line length**: 120 characters
- **Quote style**: Double quotes
- **Formatter**: black + isort
- **Linter**: ruff + mypy
- **Import order**: Standard library → third-party → local modules

```python
# Example import structure
import json
import logging
from typing import Annotated

from fastmcp import Context
from mcp.types import TextContent

from . import auth_helper
from .common import get_user_id_description
```

### Type Hints
- Use `Annotated[type, "description"]` for function parameters
- Use `str | None` instead of `Optional[str]` (PEP 604)
- Use `list[T]` instead of `List[T]` (built-in generics)

### Naming Conventions
- Functions/variables: `snake_case`
- Classes: `PascalCase`
- Constants: `UPPER_SNAKE_CASE`
- Private members: prefix with `_`

### Architecture Patterns

#### Module Structure
```
src/mcp_gsuite/
├── fast_server.py      # MCP server entry point
├── settings.py         # Configuration via pydantic-settings
├── gauth.py            # Google OAuth authentication
├── auth_helper.py      # Authentication utilities
├── common.py           # Shared utilities
├── gmail.py            # Gmail service layer
├── gmail_tools.py      # Gmail MCP tools
├── calendar.py         # Calendar service layer
├── calendar_tools.py   # Calendar MCP tools
├── drive.py            # Drive service layer
├── drive_tools.py      # Drive MCP tools
└── gmail_drive_tools.py # Gmail-Drive integration tools
```

#### Tool Pattern
Each Google service follows a two-layer pattern:
1. **Service layer** (`gmail.py`, `calendar.py`, `drive.py`) - Direct Google API interactions
2. **Tools layer** (`gmail_tools.py`, etc.) - MCP tool definitions using fastmcp decorators

### Testing Strategy

#### Unit Tests
- Location: `tests/unit/`
- Framework: `unittest.TestCase` with pytest runner
- Mock external services (Gmail, Calendar APIs)
- Run: `make test` or `uv run pytest tests/unit`

#### E2E Tests
- Location: `tests/e2e/`
- Marker: `@pytest.mark.e2e`
- Requires real Google credentials in `.env.local`
- Run: `make e2e-tests` (skipped in CI)

#### Test Commands
```bash
make test                    # Run unit tests
make coverage               # Run with coverage report
make e2e-tests              # Run E2E tests (requires credentials)
```

### Git Workflow

#### Branching
- Main branch: `main`
- Feature branches for development

#### Release Process
1. Update version in `pyproject.toml`
2. Commit changes
3. Tag with version (e.g., `v0.4.2`)
4. Push tag triggers automatic PyPI publish

```bash
make bump-patch  # 0.4.1 -> 0.4.2
make bump-minor  # 0.4.1 -> 0.5.0
make bump-major  # 0.4.1 -> 1.0.0
```

## Domain Context

### MCP (Model Context Protocol)
MCP is a protocol that allows AI assistants to interact with external tools and services. This server exposes Google Workspace functionality as MCP tools that Claude and other compatible AI assistants can call.

### Google OAuth2 Authentication
- Uses OAuth2 desktop/web application flow
- Credentials stored in `.gauth.json` (client config) and `.oauth2.{email}.json` (tokens)
- Supports multiple Google accounts via `.accounts.json`
- Required scopes: Gmail, Calendar, Drive, userinfo.email

## Important Constraints

- **Python version**: Requires Python 3.13+
- **fastmcp version**: Pinned to 2.1.x to avoid breaking changes
- **OAuth2 setup**: Initial browser-based authentication required before server use
- **E2E tests**: Cannot run in CI (require real Google credentials)
- **Rate limits**: Subject to Google API quotas

## External Dependencies

### Google APIs
- Gmail API - Email operations
- Google Calendar API - Calendar management
- Google Drive API - File storage and management

### Authentication Services
- Google OAuth2 - User authentication
- Google Cloud Console - API credentials management

### Development Tools
- PyPI - Package distribution
- GitHub Actions - CI/CD pipeline
- codecov - Code coverage tracking
