"""Read the book catalog and search it."""
from __future__ import annotations

import csv
from pathlib import Path

from .models import Book

DATA_DIR = Path(__file__).resolve().parents[2] / "data"


def load_books(path: Path | None = None) -> list[Book]:
    with open(path or DATA_DIR / "books.csv", newline="", encoding="utf-8") as handle:
        return [
            Book(row["isbn"], row["title"], row["author"], int(row["year"]), int(row["copies"]))
            for row in csv.DictReader(handle)
        ]


def find_by_isbn(books: list[Book], isbn: str) -> Book | None:
    for book in books:
        if book.isbn == isbn:
            return book
    return None


def search_by_title(books: list[Book], query: str) -> list[Book]:
    """Return the books whose title contains the query, ignoring upper or lower case."""
    return [b for b in books if query in b.title]


def books_by_author(books: list[Book], author: str) -> list[Book]:
    return [b for b in books if b.author == author]
