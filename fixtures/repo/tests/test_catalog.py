from shelf.catalog import books_by_author, find_by_isbn, load_books, search_by_title


def test_load_books_count():
    assert len(load_books()) == 6


def test_find_by_isbn():
    book = find_by_isbn(load_books(), "9780441172719")
    assert book is not None and book.title == "Dune"


def test_search_is_case_insensitive():
    titles = [b.title for b in search_by_title(load_books(), "dune")]
    assert titles == ["Dune"]


def test_books_by_author():
    assert [b.title for b in books_by_author(load_books(), "George Orwell")] == ["Nineteen Eighty-Four"]
