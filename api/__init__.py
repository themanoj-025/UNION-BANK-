"""
api  –  Union Bank REST API package.

Provides versioned API routers mounted under different prefixes:
- /api/v1/  (legacy — bare response models, backward compatible)
- /api/v2/  (current — envelope-wrapped ApiResponse[T], enhanced metadata)

The main FastAPI app in api.py mounts both routers.
"""
