"""savings.py  –  Savings goals persistence helpers.

Uses the container (SQLite) instead of JSON files for storage.
Falls back to JSON for backward compatibility during migration.
"""

from decimal import Decimal


def load_goals(acc_no: str) -> list:
    """Load savings goals for a specific account from SQLite."""
    from infrastructure.container import get_container
    c = get_container()
    domain_goals = c.savings_goal_service().list_goals(acc_no)
    return [{
        "goal_id": g.goal_id,
        "name": g.name,
        "target_amount": float(g.target_amount),
        "current_amount": float(g.current_amount),
        "target_date": g.target_date or "",
        "created_at": str(g.created_at)[:19],
        "is_completed": g.is_completed,
    } for g in domain_goals]


def save_goals(acc_no: str, goals: list) -> None:
    """Save savings goals for a specific account to SQLite.

    Note: This replaces ALL goals for the account with the provided list.
    For fine-grained operations, use the container's SavingsGoalService directly.
    """
    from infrastructure.container import get_container
    from domain.entities import SavingsGoal
    c = get_container()
    goal_repo = c.savings_goal_repo()

    # Delete existing goals for this account
    existing = goal_repo.get_by_account(acc_no)
    for goal in existing:
        goal_repo.delete(goal.goal_id)

    # Re-create from provided list
    for g in goals:
        domain_goal = SavingsGoal(
            goal_id=g.get("goal_id", ""),
            account_number=acc_no,
            name=g.get("name", ""),
            target_amount=Decimal(str(g.get("target_amount", 0))),
            current_amount=Decimal(str(g.get("current_amount", 0))),
            target_date=g.get("target_date") or None,
            is_completed=g.get("is_completed", False),
        )
        goal_repo.create(domain_goal)
    goal_repo.commit()
