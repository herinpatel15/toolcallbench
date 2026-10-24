"""Late-fee rules."""
from __future__ import annotations

from datetime import date


def days_late(due_on: date, returned_on: date) -> int:
    """Whole days a book is overdue; 0 when it is returned on time."""
    return max((returned_on - due_on).days, 0)


def late_fee(days: int, per_day: float, cap: float | None = None) -> float:
    """Fee for a late return.

    The fee grows by `per_day` for every late day but never goes above `cap`
    when a cap is given.
    """
    if days <= 0:
        return 0.0
    return round(days * per_day, 2)
