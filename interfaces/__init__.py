"""Interfaces layer — CLI, Web, and API entry points.

Each interface depends only on the application layer via the DI container.
Never directly imports infrastructure or uses JSON file I/O.
"""
