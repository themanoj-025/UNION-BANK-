"""
api  –  Union Bank REST API package.

Provides versioned API routers mounted under different prefixes:
- /api/v1/  (legacy — bare response models, backward compatible)
- /api/v2/  (current — envelope-wrapped ApiResponse[T], enhanced metadata)

The main FastAPI app is defined in the root-level `api.py` module.
This ``__init__.py`` re-exports ``app`` so that imports like
``from api import app`` work despite the package shadowing the module.

Note: The root `api.py` imports from this package (`api.models`,
`api.common`, `api.v2`), so we must avoid circular imports by using
a deferred import strategy.
"""

from __future__ import annotations

import importlib.util as _ilu
import os as _os
import sys as _sys

# Locate and load the root-level ``api.py`` module.
# We cannot use ``from api import app`` here because the ``api/`` package
# shadows the root ``api.py`` module. Instead we load it by file path.
_this_dir = _os.path.dirname(_os.path.abspath(__file__))
_project_root = _os.path.dirname(_this_dir)
_api_py = _os.path.join(_project_root, "api.py")

if _os.path.isfile(_api_py):
    _spec = _ilu.spec_from_file_location("_api_root_module", _api_py)
    if _spec and _spec.loader:
        _mod = _ilu.module_from_spec(_spec)
        _spec.loader.exec_module(_mod)
        app = _mod.app  # noqa: F811 — re-export for ``from api import app``
else:
    # Fallback: when api.py doesn't exist (e.g., during restructuring),
    # the app will be defined here in the future.
    from fastapi import FastAPI
    app = FastAPI(title="Union Bank API")  # noqa: F811
