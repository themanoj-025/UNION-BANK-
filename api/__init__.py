"""
api  –  Union Bank REST API package.

Provides versioned API routers mounted under different prefixes:
- /api/v1/  (legacy — bare response models, backward compatible)
- /api/v2/  (current — envelope-wrapped ApiResponse[T], enhanced metadata)

The main FastAPI app in api.py (project root) defines the FastAPI application.
This __init__.py re-exports ``app`` so that ``from api import app`` works
even though the ``api/`` package directory shadows the root-level module.
"""

import importlib.util as _ilu
import os as _os
import sys as _sys

# Locate the root-level ``api.py`` file (NOT this package).
_this_dir = _os.path.dirname(_os.path.abspath(__file__))
_project_root = _os.path.dirname(_this_dir)
_api_py = _os.path.join(_project_root, "api.py")

if _os.path.isfile(_api_py):
    _spec = _ilu.spec_from_file_location("_api_root_module", _api_py)
    if _spec and _spec.loader:
        _mod = _ilu.module_from_spec(_spec)
        _spec.loader.exec_module(_mod)
        app = _mod.app  # noqa: F811 — re-export for ``from api import app``
