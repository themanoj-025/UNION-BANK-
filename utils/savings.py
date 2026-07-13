"""
savings.py  –  Savings goals persistence helpers.
"""

from .file_io import load_json, save_json, SAVINGS_GOALS_FILE


def load_goals(acc_no: str) -> list:
    """Load savings goals for a specific account."""
    all_goals = load_json(SAVINGS_GOALS_FILE)
    return all_goals.get(acc_no, [])


def save_goals(acc_no: str, goals: list) -> None:
    """Save savings goals for a specific account."""
    all_goals = load_json(SAVINGS_GOALS_FILE)
    all_goals[acc_no] = goals
    save_json(SAVINGS_GOALS_FILE, all_goals)
