from __future__ import annotations

from aiogram.fsm.state import State, StatesGroup


class SearchStates(StatesGroup):
    waiting_filter_value = State()

