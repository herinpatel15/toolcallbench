from shelf.utils import format_money, isbn_ok, slugify


def test_format_money():
    assert format_money(2.5) == "2.50 USD"


def test_slugify():
    assert slugify("The Great Gatsby!") == "the-great-gatsby"


def test_isbn_ok():
    assert isbn_ok("9780441172719")
    assert not isbn_ok("12345")
