"""Borrowing and returning books."""
from __future__ import annotations

from datetime import date, timedelta

from .fees import days_late, late_fee
from .models import Book, Loan


class LoanError(Exception):
    """Raised when a loan request is not allowed."""


class Library:
    def __init__(self, books: list[Book], settings: dict):
        self.settings = settings
        self.stock = {book.isbn: book.copies for book in books}
        self.loans: list[Loan] = []

    def available_copies(self, isbn: str) -> int:
        if isbn not in self.stock:
            raise LoanError(f"unknown ISBN {isbn}")
        active = sum(1 for loan in self.loans if loan.isbn == isbn and loan.returned_on is None)
        return self.stock[isbn] - active

    def loans_for(self, member_id: str) -> list[Loan]:
        return [loan for loan in self.loans if loan.member_id == member_id and loan.returned_on is None]

    def borrow(self, isbn: str, member_id: str, today: date) -> Loan:
        if self.available_copies(isbn) <= 0:
            raise LoanError("no copies available")
        if len(self.loans_for(member_id)) >= self.settings["max_loans_per_member"]:
            raise LoanError("loan limit reached")
        due = today + timedelta(days=self.settings["loan_days"])
        loan = Loan(isbn, member_id, today, due)
        self.loans.append(loan)
        return loan

    def return_book(self, isbn: str, member_id: str, today: date) -> float:
        """Mark a loan as returned and return the late fee owed."""
        for loan in self.loans_for(member_id):
            if loan.isbn == isbn:
                loan.returned_on = today
                late = days_late(loan.due_on, today)
                return late_fee(late, self.settings["late_fee_per_day"], self.settings["max_late_fee"])
        raise LoanError("no such loan")
