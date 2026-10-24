"""Plain data classes."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date


@dataclass(frozen=True)
class Book:
    isbn: str
    title: str
    author: str
    year: int
    copies: int


@dataclass(frozen=True)
class Member:
    member_id: str
    name: str
    joined: date


@dataclass
class Loan:
    isbn: str
    member_id: str
    borrowed_on: date
    due_on: date
    returned_on: date | None = None
