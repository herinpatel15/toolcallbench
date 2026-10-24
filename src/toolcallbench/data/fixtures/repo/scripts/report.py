"""Print a short summary of the library."""
import csv
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from shelf.catalog import load_books  # noqa: E402


def main() -> None:
    books = load_books()
    with open(ROOT / "data" / "members.csv", newline="", encoding="utf-8") as handle:
        members = list(csv.DictReader(handle))
    print("Library report")
    print(f"Titles: {len(books)}")
    print(f"Copies: {sum(b.copies for b in books)}")
    print(f"Members: {len(members)}")


if __name__ == "__main__":
    main()
