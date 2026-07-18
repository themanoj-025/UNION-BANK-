"""
Union Bank test suite.

Organized by layer:
  - test_utils.py:        Unit tests for utility functions
  - test_features.py:     Feature tests (rate limiting, CSV, interest, atomic transfers)
  - test_smoke.py:        Module import smoke tests
  - test_services.py:     Unit tests for application services (in-memory fakes)
  - test_property_based.py: Hypothesis property-based tests for money invariants
  - test_integration.py:  Integration tests with real SQLite via DI container
  - fakes.py:             In-memory repository fakes for fast unit testing
"""
