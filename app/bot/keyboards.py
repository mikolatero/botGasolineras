from __future__ import annotations

from aiogram.filters.callback_data import CallbackData
from aiogram.types import InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder

from app.config.constants import FUEL_BY_ID
from app.models.enums import WatchlistStatus
from app.utils.formatting import format_compact_price


class SearchMenuCallback(CallbackData, prefix="searchmenu"):
    action: str
    value: str


class SearchResultCallback(CallbackData, prefix="searchresult"):
    action: str
    value: str
    page: int


class StationFuelCallback(CallbackData, prefix="stationfuel"):
    station_id: str
    fuel_id: int
    page: int


class WatchlistCallback(CallbackData, prefix="watchlist"):
    action: str
    watchlist_id: int
    page: int


FILTER_LABELS = {
    "postal_code": "CP",
    "radius_km": "Radio km",
    "province": "Provincia",
    "municipality": "Municipio",
    "locality": "Localidad",
    "brand": "Marca",
    "address_text": "Direccion",
    "fuel_id": "Combustible",
}


def build_search_menu(filters: dict[str, str | int | None]):
    builder = InlineKeyboardBuilder()
    for field, label in FILTER_LABELS.items():
        builder.button(text=label, callback_data=SearchMenuCallback(action="set", value=field).pack())
    builder.button(text="Buscar ahora", callback_data=SearchMenuCallback(action="run", value="0").pack())
    builder.button(text="Limpiar filtros", callback_data=SearchMenuCallback(action="clear", value="0").pack())
    builder.adjust(2, 2, 2, 2, 2)
    return builder.as_markup()


def build_fuel_picker(prefix: str):
    builder = InlineKeyboardBuilder()
    for fuel_id in sorted(FUEL_BY_ID):
        builder.button(
            text=str(FUEL_BY_ID[fuel_id]["name"]),
            callback_data=SearchMenuCallback(action=prefix, value=str(fuel_id)).pack(),
        )
    builder.adjust(2)
    return builder.as_markup()


def build_search_results(stations, page: int, total: int, page_size: int):
    builder = InlineKeyboardBuilder()
    for station in stations:
        label = f"{station.brand} | {station.municipality} | {station.address[:28]}"
        builder.button(text=label, callback_data=SearchResultCallback(action="station", value=station.ideess, page=page).pack())
    if page > 1:
        builder.button(text="⬅️ Anterior", callback_data=SearchResultCallback(action="page", value=str(page - 1), page=page - 1).pack())
    if page * page_size < total:
        builder.button(text="Siguiente ➡️", callback_data=SearchResultCallback(action="page", value=str(page + 1), page=page + 1).pack())
    builder.button(text="Editar filtros", callback_data=SearchResultCallback(action="filters", value="0", page=page).pack())
    builder.adjust(1, 2, 1)
    return builder.as_markup()


def build_station_fuels(station_id: str, station_fuels, page: int):
    builder = InlineKeyboardBuilder()
    for fuel, price in station_fuels:
        builder.button(
            text=f"{fuel.name} | {price.current_price:.3f} €/L",
            callback_data=StationFuelCallback(station_id=station_id, fuel_id=fuel.id, page=page).pack(),
        )
    builder.button(text="Volver a resultados", callback_data=SearchResultCallback(action="page", value=str(page), page=page).pack())
    builder.adjust(1)
    return builder.as_markup()


def build_watchlist_actions(watchlists, page: int, total: int, page_size: int, price_map: dict[tuple[str, int], object] | None = None):
    builder = InlineKeyboardBuilder()
    price_map = price_map or {}
    for watchlist in watchlists:
        status = "⏸" if watchlist.status == WatchlistStatus.PAUSED else "▶️"
        price_row = price_map.get((watchlist.station_id, watchlist.fuel_id))
        price_text = (
            f" | {format_compact_price(price_row.current_price)}"
            if price_row is not None
            else ""
        )
        builder.row(
            InlineKeyboardButton(
                text=f"{status} {watchlist.station.brand} | {watchlist.fuel.name}{price_text}",
                callback_data=WatchlistCallback(action="noop", watchlist_id=watchlist.id, page=page).pack(),
            )
        )
        builder.row(
            InlineKeyboardButton(
                text="Pausar" if watchlist.status == WatchlistStatus.ACTIVE else "Reanudar",
                callback_data=WatchlistCallback(
                    action="pause" if watchlist.status == WatchlistStatus.ACTIVE else "resume",
                    watchlist_id=watchlist.id,
                    page=page,
                ).pack(),
            ),
            InlineKeyboardButton(
                text="Eliminar",
                callback_data=WatchlistCallback(action="delete", watchlist_id=watchlist.id, page=page).pack(),
            ),
        )
    navigation_buttons = []
    if page > 1:
        navigation_buttons.append(
            InlineKeyboardButton(
                text="⬅️ Anterior",
                callback_data=WatchlistCallback(action="page", watchlist_id=0, page=page - 1).pack(),
            )
        )
    if page * page_size < total:
        navigation_buttons.append(
            InlineKeyboardButton(
                text="Siguiente ➡️",
                callback_data=WatchlistCallback(action="page", watchlist_id=0, page=page + 1).pack(),
            )
        )
    if navigation_buttons:
        builder.row(*navigation_buttons)
    return builder.as_markup()
