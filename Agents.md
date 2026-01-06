Use `uv` for dependency management.

Useful Commands

    # Sync dependencies from lockfile
    uv sync

    # Add a new package
    uv add <PACKAGE-NAME>

    # Run Python files
    uv run python <PYTHON-FILE>

    # Run tests
    uv run pytest

# Agent Instructions

## Guidelines
Before making any changes:
- Read Design.md in full
- Review any relevant files in docs/ related to the area being modified

## Change Rules
- Do not violate goals or non-goals defined in Design.md
- Preserve public APIs unless explicitly instructed
- Keep changes scoped to the requested area
- Do not introduce insecure storage or auth behavior
- Do not silently downgrade security or provider guarantees

## Documentation
- Update docs/ when behavior changes
- Do not modify Design.md unless explicitly instructed
- Add changes to changelog.md

## Uncertainty
- If a change conflicts with Design.md, stop and ask