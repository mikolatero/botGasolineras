from __future__ import annotations

from math import ceil

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from app.bot.keyboards import (
    FILTER_LABELS,
    SearchMenuCallback,
    SearchResultCallback,
    StationFuelCallback,
    WatchlistCallback,
    build_fuel_picker,
    build_search_menu,
    build_search_results,
    build_station_fuels,
    build_watchlist_actions,
)
from app.bot.states import SearchStates
from app.config.constants import FUEL_BY_ID
from app.config.database import SessionLocal
from app.config.settings import get_settings
from app.integrations.postal_code_api import CartoCiudadPostalCodeClient
from app.repositories.fuels import FuelsRepository
from app.repositories.postal_code_locations import PostalCodeLocationsRepository
from app.repositories.station_prices import StationPricesRepository
from app.repositories.stations import StationsRepository
from app.repositories.users import UsersRepository
from app.repositories.watchlists import WatchlistsRepository
from app.services.search_service import SearchFilters, SearchService
from app.services.watchlist_service import WatchlistService
from app.utils.formatting import format_compact_price
from app.utils.parsing import digits_only

router = Router()


HELP_TEXT = (
    "<b>Manual del bot</b>\n\n"
    "<b>Que hace este bot</b>\n"
    "Este bot te avisa cuando baja el precio del combustible en las gasolineras que sigues.\n"
    "No tienes que revisar precios a mano: eliges una gasolinera, eliges un combustible y el bot te notifica cuando detecta una bajada.\n\n"
    "<b>Como empezar</b>\n"
    "1. Usa <b>/buscar</b> o <b>/anadir</b>.\n"
    "2. Pon uno o varios filtros en el buscador.\n"
    "3. Pulsa <b>Buscar ahora</b>.\n"
    "4. Elige una gasolinera de la lista.\n"
    "5. Elige el combustible que quieres seguir.\n"
    "6. El bot crea el seguimiento y ya queda guardado.\n\n"
    "<b>Como funciona la busqueda</b>\n"
    "Puedes buscar por codigo postal, radio en km, provincia, municipio, localidad, marca, direccion o combustible.\n"
    "No hace falta rellenarlo todo. Cuantos mas filtros pongas, mas afinados saldran los resultados.\n\n"
    "Consejos rapidos:\n"
    "• <b>Codigo postal</b>: muy util para empezar una busqueda cercana.\n"
    "• <b>Radio en KM</b>: solo funciona si antes indicas un codigo postal. El radio permitido es de 1 a 50 km.\n"
    "• <b>Provincia / municipio / localidad</b>: sirven para acotar una zona concreta.\n"
    "• <b>Marca</b>: por ejemplo Repsol, Cepsa, BP, etc.\n"
    "• <b>Direccion</b>: util si recuerdas una calle, avenida, carretera o parte de la direccion.\n"
    "• <b>Combustible</b>: filtra resultados para que luego sea mas facil elegir.\n\n"
    "Cuando termines de ajustar filtros, pulsa <b>Buscar ahora</b>. Si quieres empezar desde cero, pulsa <b>Limpiar filtros</b>.\n\n"
    "<b>Buscar o anadir</b>\n"
    "<b>/buscar</b> y <b>/anadir</b> abren el mismo buscador.\n"
    "La diferencia practica es esta:\n"
    "• usa <b>/buscar</b> si solo quieres mirar opciones\n"
    "• usa <b>/anadir</b> si ya vas con la idea de crear un seguimiento\n\n"
    "<b>Que es un seguimiento</b>\n"
    "Un seguimiento es la combinacion de una gasolinera y un combustible.\n"
    "Ejemplo: puedes seguir Gasoleo A en una estacion concreta y tambien Gasolina 95 en esa misma estacion como seguimientos distintos.\n\n"
    "<b>Cuando te avisa el bot</b>\n"
    "El bot avisa cuando detecta que el precio ha bajado respecto al ultimo precio guardado para ese seguimiento.\n"
    "Si el precio no baja, no envia aviso.\n\n"
    "<b>Mis seguimientos</b>\n"
    "Con <b>/mis_seguimientos</b> ves todos tus seguimientos guardados.\n"
    "En esa pantalla puedes revisar el estado de cada uno y gestionarlos sin volver a buscar.\n"
    "Si ves <b>Activa</b>, ese seguimiento puede generar avisos.\n"
    "Si ves <b>Pausada</b>, esta guardado pero no avisara hasta reanudarlo.\n\n"
    "<b>Pausar, reanudar y eliminar</b>\n"
    "• <b>Pausar</b>: detiene temporalmente los avisos, pero conserva el seguimiento.\n"
    "• <b>Reanudar</b>: vuelve a activar un seguimiento pausado.\n"
    "• <b>Eliminar</b>: borra el seguimiento.\n\n"
    "Los comandos <b>/pausar</b>, <b>/reanudar</b> y <b>/eliminar</b> abren el mismo gestor para que lo hagas desde la lista de seguimientos.\n\n"
    "<b>Resumen de comandos</b>\n"
    "/start - registrar usuario y mostrar ayuda corta\n"
    "/help - abrir este manual\n"
    "/buscar - abrir el buscador\n"
    "/anadir - abrir el buscador para crear un seguimiento\n"
    "/mis_seguimientos - ver tus seguimientos\n"
    "/pausar - abrir el gestor para pausar seguimientos\n"
    "/reanudar - abrir el gestor para reanudar seguimientos\n"
    "/eliminar - abrir el gestor para eliminar seguimientos"
)


def _filters_from_state(data: dict) -> SearchFilters:
    return SearchFilters(
        postal_code=data.get("postal_code"),
        radius_km=data.get("radius_km"),
        province=data.get("province"),
        municipality=data.get("municipality"),
        locality=data.get("locality"),
        brand=data.get("brand"),
        address_text=data.get("address_text"),
        fuel_id=data.get("fuel_id"),
    )


def _render_filter_summary(filters: dict[str, str | int | None]) -> str:
    parts = []
    for key, value in filters.items():
        if not value:
            continue
        label = FILTER_LABELS[key]
        display_value = value
        if key == "fuel_id":
            fuel = FUEL_BY_ID.get(int(value))
            display_value = fuel["name"] if fuel is not None else value
        parts.append(f"• <b>{label}:</b> {display_value}")
    body = "\n".join(parts) if parts else "• Sin filtros todavia"
    return (
        "<b>Buscador de gasolineras</b>\n"
        "Configura uno o varios filtros y pulsa <b>Buscar ahora</b>.\n\n"
        f"{body}"
    )


def _render_search_results_text(stations, page: int, total: int, page_size: int) -> str:
    total_pages = max(1, ceil(total / page_size))
    lines = [f"<b>Resultados</b> ({total}) - pagina {page}/{total_pages}"]
    for idx, station in enumerate(stations, start=1 + (page - 1) * page_size):
        price = getattr(station, "search_price", None)
        price_text = f" | {format_compact_price(price)}" if price is not None else ""
        lines.append(
            f"{idx}. <b>{station.brand}</b> - {station.address}, {station.municipality} "
            f"({station.postal_code_display or 's/cp'}){price_text}"
        )
    return "\n".join(lines)


def _render_watchlists_text(watchlists, page: int, total: int, page_size: int, price_map: dict[tuple[str, int], object] | None = None) -> str:
    price_map = price_map or {}
    total_pages = max(1, ceil(total / page_size))
    lines = [f"<b>Mis seguimientos</b> ({total}) - pagina {page}/{total_pages}"]
    if not watchlists:
        lines.append("Todavia no tienes seguimientos.")
    for watchlist in watchlists:
        status = "Activa" if watchlist.status.value == "active" else "Pausada"
        price_row = price_map.get((watchlist.station_id, watchlist.fuel_id))
        price_text = f" | {format_compact_price(price_row.current_price)}" if price_row is not None else ""
        lines.append(
            f"<b>{watchlist.station.brand}</b> - {watchlist.station.address}, "
            f"{watchlist.station.municipality} | {watchlist.fuel.name}{price_text} | {status}"
        )
    return "\n".join(lines)


async def _ensure_user(message_or_callback) -> int:
    user = message_or_callback.from_user
    async with SessionLocal() as session:
        repository = UsersRepository(session)
        db_user = await repository.get_or_create(user)
        await session.commit()
        return db_user.id


async def _show_search_menu(target: Message | CallbackQuery, state: FSMContext) -> None:
    data = await state.get_data()
    filters = {
        "postal_code": data.get("postal_code"),
        "radius_km": data.get("radius_km"),
        "province": data.get("province"),
        "municipality": data.get("municipality"),
        "locality": data.get("locality"),
        "brand": data.get("brand"),
        "address_text": data.get("address_text"),
        "fuel_id": data.get("fuel_id"),
    }
    text = _render_filter_summary(filters)
    markup = build_search_menu(filters)
    if isinstance(target, Message):
        await target.answer(text, reply_markup=markup)
    else:
        await target.message.edit_text(text, reply_markup=markup)
        await target.answer()


async def _run_search(callback: CallbackQuery, state: FSMContext, page: int) -> None:
    settings = get_settings()
    data = await state.get_data()
    filters = _filters_from_state(data)
    if filters.radius_km and not filters.postal_code:
        await callback.message.edit_text(
            "El filtro de radio requiere que indiques tambien un codigo postal.",
            reply_markup=build_search_menu(filters.as_dict()),
        )
        await callback.answer()
        return
    async with SessionLocal() as session:
        service = SearchService(
            StationsRepository(session),
            PostalCodeLocationsRepository(session),
            CartoCiudadPostalCodeClient(settings),
        )
        stations, total = await service.search(filters, page=page, page_size=settings.search_result_page_size)
        await session.commit()
    if not stations:
        await callback.message.edit_text("No he encontrado gasolineras con esos filtros. Ajusta la busqueda.", reply_markup=build_search_menu(filters.as_dict()))
        await callback.answer()
        return
    text = _render_search_results_text(stations, page, total, settings.search_result_page_size)
    await callback.message.edit_text(
        text,
        reply_markup=build_search_results(stations, page, total, settings.search_result_page_size),
    )
    await callback.answer()


async def _show_watchlists(target: Message | CallbackQuery, user_id: int, page: int) -> None:
    settings = get_settings()
    async with SessionLocal() as session:
        service = WatchlistService(WatchlistsRepository(session))
        watchlists, total = await service.list_user_watchlists(user_id, page, settings.watchlist_page_size)
        price_map = await StationPricesRepository(session).load_current_price_map_for_pairs(
            (watchlist.station_id, watchlist.fuel_id) for watchlist in watchlists
        )
    text = _render_watchlists_text(watchlists, page, total, settings.watchlist_page_size, price_map)
    markup = build_watchlist_actions(watchlists, page, total, settings.watchlist_page_size, price_map)
    if isinstance(target, Message):
        await target.answer(text, reply_markup=markup)
    else:
        await target.message.edit_text(text, reply_markup=markup)
        await target.answer()


@router.message(Command("start"))
async def start_handler(message: Message, state: FSMContext) -> None:
    await _ensure_user(message)
    await state.clear()
    await message.answer(
        "Bot publico para seguir bajadas de precio en gasolineras de Espana.\n"
        "Usa /buscar o /anadir para empezar.\n\n"
        f"{HELP_TEXT}"
    )


@router.message(Command("help"))
async def help_handler(message: Message) -> None:
    await _ensure_user(message)
    await message.answer(HELP_TEXT)


@router.message(Command("buscar"))
@router.message(Command("anadir"))
async def search_entry_handler(message: Message, state: FSMContext) -> None:
    await _ensure_user(message)
    await state.clear()
    await _show_search_menu(message, state)


@router.message(Command("mis_seguimientos"))
@router.message(Command("eliminar"))
@router.message(Command("pausar"))
@router.message(Command("reanudar"))
async def watchlists_handler(message: Message) -> None:
    user_id = await _ensure_user(message)
    await _show_watchlists(message, user_id, page=1)


@router.callback_query(SearchMenuCallback.filter(F.action == "set"))
async def search_menu_set_handler(callback: CallbackQuery, callback_data: SearchMenuCallback, state: FSMContext) -> None:
    field = callback_data.value
    if field == "fuel_id":
        await callback.message.edit_text("Selecciona un combustible para filtrar los resultados.", reply_markup=build_fuel_picker("fuel"))
        await callback.answer()
        return
    await state.update_data(editing_field=field)
    await state.set_state(SearchStates.waiting_filter_value)
    await callback.message.answer(f"Escribe el valor para <b>{FILTER_LABELS[field]}</b>.")
    await callback.answer()


@router.callback_query(SearchMenuCallback.filter(F.action == "fuel"))
async def fuel_filter_handler(callback: CallbackQuery, callback_data: SearchMenuCallback, state: FSMContext) -> None:
    await state.update_data(fuel_id=int(callback_data.value))
    await _show_search_menu(callback, state)


@router.callback_query(SearchMenuCallback.filter(F.action == "run"))
async def search_run_handler(callback: CallbackQuery, state: FSMContext) -> None:
    await _run_search(callback, state, page=1)


@router.callback_query(SearchMenuCallback.filter(F.action == "clear"))
async def search_clear_handler(callback: CallbackQuery, state: FSMContext) -> None:
    await state.clear()
    await _show_search_menu(callback, state)


@router.message(SearchStates.waiting_filter_value)
async def search_value_handler(message: Message, state: FSMContext) -> None:
    data = await state.get_data()
    field = data.get("editing_field")
    if not field:
        await state.clear()
        return
    value = message.text.strip()
    if field == "postal_code":
        value = digits_only(value) or ""
        if len(value) not in {5}:
            await message.answer("El codigo postal debe tener 5 digitos.")
            return
    if field == "radius_km":
        if not value.isdigit():
            await message.answer("El radio debe ser un numero entero de kilometros.")
            return
        radius_km = int(value)
        if radius_km < 1 or radius_km > 50:
            await message.answer("El radio debe estar entre 1 y 50 km.")
            return
        value = radius_km
    await state.update_data({field: value, "editing_field": None})
    await state.set_state(None)
    await _show_search_menu(message, state)


@router.callback_query(SearchResultCallback.filter(F.action == "page"))
async def result_page_handler(callback: CallbackQuery, callback_data: SearchResultCallback, state: FSMContext) -> None:
    await _run_search(callback, state, page=int(callback_data.value))


@router.callback_query(SearchResultCallback.filter(F.action == "filters"))
async def result_filters_handler(callback: CallbackQuery, state: FSMContext) -> None:
    await _show_search_menu(callback, state)


@router.callback_query(SearchResultCallback.filter(F.action == "station"))
async def station_select_handler(callback: CallbackQuery, callback_data: SearchResultCallback) -> None:
    async with SessionLocal() as session:
        service = SearchService(StationsRepository(session))
        station = await StationsRepository(session).get_by_ideess(callback_data.value)
        station_fuels = await service.list_station_fuels(callback_data.value)
    if station is None or not station_fuels:
        await callback.answer("La estacion no tiene combustibles disponibles ahora mismo.", show_alert=True)
        return
    text = (
        f"<b>{station.brand}</b>\n"
        f"{station.address}, {station.municipality} ({station.postal_code_display or 's/cp'})\n"
        f"Horario: {station.schedule or 'No disponible'}\n\n"
        "Selecciona el combustible para crear el seguimiento."
    )
    await callback.message.edit_text(text, reply_markup=build_station_fuels(station.ideess, station_fuels, callback_data.page))
    await callback.answer()


@router.callback_query(StationFuelCallback.filter())
async def station_fuel_handler(callback: CallbackQuery, callback_data: StationFuelCallback) -> None:
    user_id = await _ensure_user(callback)
    async with SessionLocal() as session:
        watchlist_service = WatchlistService(WatchlistsRepository(session))
        stations_repository = StationsRepository(session)
        fuels_repository = FuelsRepository(session)
        station = await stations_repository.get_by_ideess(callback_data.station_id)
        fuel = await fuels_repository.get_by_id(callback_data.fuel_id)
        if station is None or fuel is None:
            await callback.answer("No he podido crear el seguimiento.", show_alert=True)
            return
        _, created = await watchlist_service.subscribe(user_id, station.ideess, fuel.id)
        await session.commit()
    status_text = "Seguimiento creado" if created else "Seguimiento reactivado"
    await callback.message.edit_text(
        f"<b>{status_text}</b>\n{station.brand} - {station.address}, {station.municipality}\nCombustible: {fuel.name}"
    )
    await callback.answer()


@router.callback_query(WatchlistCallback.filter(F.action == "page"))
async def watchlist_page_handler(callback: CallbackQuery, callback_data: WatchlistCallback) -> None:
    user_id = await _ensure_user(callback)
    await _show_watchlists(callback, user_id, page=callback_data.page)


@router.callback_query(WatchlistCallback.filter(F.action.in_({"pause", "resume", "delete"})))
async def watchlist_action_handler(callback: CallbackQuery, callback_data: WatchlistCallback) -> None:
    user_id = await _ensure_user(callback)
    async with SessionLocal() as session:
        repository = WatchlistsRepository(session)
        watchlist = await repository.get_for_user(user_id, callback_data.watchlist_id)
        if watchlist is None:
            await callback.answer("Seguimiento no encontrado.", show_alert=True)
            return
        if callback_data.action == "pause":
            from app.utils.timezone import now_madrid

            await repository.pause(watchlist, now_madrid())
        elif callback_data.action == "resume":
            await repository.resume(watchlist)
        else:
            await repository.delete(watchlist)
        await session.commit()
    await _show_watchlists(callback, user_id, page=callback_data.page)


@router.callback_query(WatchlistCallback.filter(F.action == "noop"))
async def watchlist_noop_handler(callback: CallbackQuery) -> None:
    await callback.answer()
