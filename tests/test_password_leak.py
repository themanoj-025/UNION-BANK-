"""
tests/test_password_leak.py  –  Verify password hash is never leaked in API responses.

The get_current_customer() dependency previously returned the bcrypt password hash
in every authenticated response. This test asserts that no API response schema
contains the string "password" as a serialized key.

This runs as a unit test against the response schema models, not the full API,
so it doesn't depend on TestClient or database connectivity.
"""

from __future__ import annotations

import ast
from pathlib import Path

# Resolve the path to api/common.py (now lives in src/unionbank/entrypoints/api/)
_COMMON_PY_PATH = (
    Path(__file__).resolve().parent.parent
    / "src" / "unionbank" / "entrypoints" / "api" / "common.py"
)


def _get_all_response_model_fields() -> dict[str, set[str]]:
    """
    Inspect all response Pydantic model field names for password leaks.

    Checks every v2 response model defined in api/models.py.
    Fields named "password" or containing "password" are security vulnerabilities.

    This does NOT import the FastAPI app — only the Pydantic models —
    so it avoids triggering database initialization or other side effects.
    """
    models_with_password = {}

    from unionbank.entrypoints.api.models import (
        AccountListItem,
        BalanceData,
        EMIPreviewData,
        HealthData,
        LoanAdminStats,
        LoanOut,
        LoanSummaryData,
        MessageData,
        ProfileData,
        SavingsGoalOut,
        SavingsGoalsSummary,
        StatisticsData,
        TokenData,
        TransactionOut,
    )

    all_response_models: list[tuple[str, type]] = [
        ("AccountListItem", AccountListItem),
        ("BalanceData", BalanceData),
        ("HealthData", HealthData),
        ("MessageData", MessageData),
        ("ProfileData", ProfileData),
        ("StatisticsData", StatisticsData),
        ("TokenData", TokenData),
        ("TransactionOut", TransactionOut),
        ("SavingsGoalOut", SavingsGoalOut),
        ("SavingsGoalsSummary", SavingsGoalsSummary),
        ("LoanOut", LoanOut),
        ("LoanSummaryData", LoanSummaryData),
        ("LoanAdminStats", LoanAdminStats),
        ("EMIPreviewData", EMIPreviewData),
    ]

    for name, model in all_response_models:
        fields = set(model.model_fields.keys())
        password_fields = {f for f in fields if "password" in f.lower()}
        if password_fields:
            models_with_password[name] = password_fields

    return models_with_password


def _get_current_customer_return_dict() -> list[str]:
    """
    Extract the keys of the return dict from get_current_customer() in api/common.py.

    Uses AST parsing to find the function and the dict literal it returns.
    Returns a list of all keys in that dict.
    """
    with open(_COMMON_PY_PATH, encoding="utf-8") as f:
        tree = ast.parse(f.read())

    for node in ast.walk(tree):
        # Handle both sync (FunctionDef) and async (AsyncFunctionDef) functions
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            if node.name == "get_current_customer":
                for subnode in ast.walk(node):
                    # Look for the final return dict literal
                    if isinstance(subnode, ast.Return) and isinstance(subnode.value, ast.Dict):
                        return [
                            key.value for key in subnode.value.keys
                            if isinstance(key, ast.Constant)
                        ]
    return []


class TestNoPasswordLeak:
    """Assert that no API response schema or internal dict ever exposes a password."""

    def test_no_response_model_has_password_field(self):
        """Verify that every Pydantic response model lacks a 'password' field."""
        leaks = _get_all_response_model_fields()
        assert not leaks, (
            f"The following response models contain password-related fields, "
            f"which should never be serialized: {leaks}"
        )

    def test_get_current_customer_does_not_return_password(self):
        """
        Verify that get_current_customer() in api/common.py does not include password.

        Parses the return dict keys from the AST and asserts 'password' is absent.
        This is a compile-time regression check — if someone re-adds the password key,
        this test will fail instantly.
        """
        return_keys = _get_current_customer_return_dict()
        assert len(return_keys) > 0, (
            "Could not find the return dict in get_current_customer(). "
            "The function may have been renamed or restructured."
        )
        assert "password" not in return_keys, (
            f"SECURITY VULNERABILITY: 'password' is a key in the return dict of "
            f"get_current_customer(). This leaks the bcrypt hash in every "
            f"authenticated API response. Remove it immediately.\n"
            f"Current keys: {return_keys}"
        )

    def test_password_not_in_profile_response(self):
        """Verify ProfileData model doesn't contain any password fields."""
        from unionbank.entrypoints.api.models import ProfileData
        fields = ProfileData.model_fields
        assert "password" not in fields, (
            "ProfileData should never include a password field. "
            "Password hash was previously leaked in this response model."
        )
        assert "current_password" not in fields
        assert "new_password" not in fields
