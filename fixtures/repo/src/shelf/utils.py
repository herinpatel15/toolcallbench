"""Small helpers used across the shelf package."""
from __future__ import annotations

import re


def format_money(amount: float, currency: str = "USD") -> str:
    """Format an amount such as 2.5 as '2.50 USD'."""
    return f"{amount:.2f} {currency}"


def slugify(text: str) -> str:
    """Turn a title into a lowercase, dash-separated slug."""
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")


def isbn_ok(isbn: str) -> bool:
    """Return True when the ISBN is 13 digits long."""
    return len(isbn) == 13 and isbn.isdigit()
