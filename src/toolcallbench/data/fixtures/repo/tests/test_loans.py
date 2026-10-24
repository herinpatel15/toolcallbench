from datetime import date, timedelta

import pytest

from shelf.catalog import load_books
from shelf.loans import Library, LoanError
from shelf.settings import load_settings

TODAY = date(2024, 5, 1)


@pytest.fixture
def library():
    return Library(load_books(), load_settings())


def test_borrow_reduces_available_copies(library):
    library.borrow("9780441172719", "M001", TODAY)
    assert library.available_copies("9780441172719") == 1


def test_loan_limit(library):
    for isbn in ("9780441172719", "9780547928227", "9780142437179"):
        library.borrow(isbn, "M001", TODAY)
    with pytest.raises(LoanError):
        library.borrow("9780743273565", "M001", TODAY)


def test_late_return_pays_fee(library):
    library.borrow("9780547928227", "M002", TODAY)
    fee = library.return_book("9780547928227", "M002", TODAY + timedelta(days=18))
    assert fee == 1.0
