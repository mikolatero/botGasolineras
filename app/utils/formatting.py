from __future__ import annotations

from decimal import Decimal

from app.models.notification import NotificationSent
from app.utils.timezone import as_madrid_datetime


def format_price(value: Decimal) -> str:
    return f"{value:.3f} €/L"


def format_compact_price(value: Decimal) -> str:
    return f"{value:.3f}€/L"


def format_notification_message(notification: NotificationSent) -> str:
    station = notification.station
    fuel = notification.fuel
    delta = notification.previous_price - notification.new_price
    timestamp = as_madrid_datetime(notification.dataset_timestamp).strftime("%d/%m/%Y %H:%M")
    return (
        "⛽ <b>Ha bajado el precio!</b>\n"
        f"📍 <b>{station.brand}</b> — {station.address}, {station.municipality}\n"
        f"🛢 <b>{fuel.name}</b>\n"
        f"💸 Antes: <b>{format_price(notification.previous_price)}</b>\n"
        f"💚 Ahora: <b>{format_price(notification.new_price)}</b>\n"
        f"📉 -{format_price(delta)}\n"
        f"🕒 {timestamp}"
    )
