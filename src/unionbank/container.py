"""container.py  –  Backward-compatible shim.

After the refactoring, the container module moved to
infrastructure/container.py. This shim exists so that existing
imports like ``from container import get_container`` continue
to work while the codebase is updated.

New code should import directly from infrastructure.container.
"""

from infrastructure.container import (  # noqa: F401
    Container,
    get_container,
    reset_container,
)
