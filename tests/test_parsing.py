from decimal import Decimal

from app.utils.parsing import parse_coordinate, parse_dataset_datetime, parse_decimal


def test_parse_decimal_with_comma() -> None:
    assert parse_decimal("1,459") == Decimal("1.459")


def test_parse_decimal_invalid_returns_none() -> None:
    assert parse_decimal("") is None
    assert parse_decimal("N/A") is None
    assert parse_decimal("0,000") is None


def test_parse_coordinate_and_datetime() -> None:
    assert parse_coordinate("37,983000") == Decimal("37.9830000")
    assert parse_dataset_datetime("25/03/2026 12:30") is not None

