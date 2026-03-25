from __future__ import annotations

import re
import unicodedata
from datetime import datetime
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from typing import Any


DECIMAL_QUANTIZER = Decimal("0.001")


def normalize_text(value: str | None) -> str | None:
    if value is None:
        return None
    cleaned = " ".join(value.strip().split())
    if not cleaned:
        return None
    ascii_text = (
        unicodedata.normalize("NFKD", cleaned).encode("ascii", "ignore").decode("ascii")
    )
    return ascii_text.casefold()


def clean_text(value: str | None) -> str | None:
    if value is None:
        return None
    cleaned = " ".join(value.strip().split())
    return cleaned or None


def parse_decimal(value: str | None) -> Decimal | None:
    if value is None:
        return None
    candidate = value.strip()
    if not candidate:
        return None
    candidate = candidate.replace(".", "").replace(",", ".")
    try:
        decimal_value = Decimal(candidate)
    except InvalidOperation:
        return None
    if decimal_value <= 0:
        return None
    return decimal_value.quantize(DECIMAL_QUANTIZER, rounding=ROUND_HALF_UP)


def parse_coordinate(value: str | None) -> Decimal | None:
    if value is None:
        return None
    candidate = value.strip()
    if not candidate:
        return None
    candidate = candidate.replace(",", ".")
    try:
        decimal_value = Decimal(candidate)
    except InvalidOperation:
        return None
    return decimal_value.quantize(Decimal("0.0000001"), rounding=ROUND_HALF_UP)


def parse_dataset_datetime(value: str | None) -> datetime | None:
    if not value:
        return None
    candidate = value.strip()
    for fmt in ("%d/%m/%Y %H:%M:%S", "%d/%m/%Y %H:%M", "%d/%m/%Y"):
        try:
            return datetime.strptime(candidate, fmt)
        except ValueError:
            continue
    return None


def digits_only(value: str | None) -> str | None:
    if value is None:
        return None
    digits = re.sub(r"\D+", "", value)
    return digits or None


def decimal_to_str(value: Decimal | None) -> str:
    if value is None:
        return "-"
    return f"{value:.3f}"


def compact_dict(data: dict[str, Any]) -> dict[str, Any]:
    return {key: value for key, value in data.items() if value is not None}

