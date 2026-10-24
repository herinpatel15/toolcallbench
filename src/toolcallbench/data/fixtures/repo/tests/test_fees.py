from datetime import date

from shelf.fees import days_late, late_fee


def test_no_fee_when_on_time():
    assert days_late(date(2024, 5, 15), date(2024, 5, 15)) == 0
    assert late_fee(0, 0.25) == 0.0


def test_fee_per_day():
    assert late_fee(4, 0.25) == 1.0


def test_late_fee_is_capped():
    assert late_fee(100, 0.25, cap=10.0) == 10.0
