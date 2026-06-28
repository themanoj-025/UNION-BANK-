## Description

Please include a summary of the changes and the related issue. What problem does this PR solve?

Fixes # (issue)

## Type of Change

- [ ] Bug fix (non-breaking change that fixes an issue)
- [ ] New feature (non-breaking change that adds functionality)
- [ ] UI/UX enhancement (CLI, Web, or API)
- [ ] Security improvement
- [ ] Documentation update
- [ ] Refactoring / code cleanup
- [ ] Breaking change (fix or feature that would cause existing functionality to change)

## Interfaces Affected

- [ ] CLI (`main.py`, `ui.py`)
- [ ] Flask Web app (`webapp.py`, templates/)
- [ ] FastAPI API (`api.py`)
- [ ] Admin panel (templates/admin_*.html)
- [ ] Banking logic (`account.py`, `bank.py`)
- [ ] Data storage / JSON files

## Testing

- [ ] `pytest tests/` — all tests pass
- [ ] CLI interface works correctly
- [ ] Flask web app loads and functions
- [ ] API endpoints return correct responses
- [ ] Tested with rate limiting (5 failed attempts / 15-min lockout)
- [ ] Tested with account freeze/unfreeze (if applicable)

## Checklist

- [ ] My code follows the existing project conventions and style
- [ ] I have updated documentation if needed
- [ ] I have added or updated environment variables if needed
- [ ] My changes do not introduce new warnings or errors
- [ ] I have tested all three interfaces (CLI, Web, API) if applicable
- [ ] I have considered security implications (see `SECURITY.md`)
- [ ] I have verified backup/corruption recovery mechanisms still work

## Additional Context

Add any other context about the PR here, such as migration notes or dependency changes.
