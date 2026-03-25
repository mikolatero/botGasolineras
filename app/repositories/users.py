from __future__ import annotations

from aiogram.types import User as TelegramUser
from sqlalchemy import select

from app.models.user import User
from app.repositories.base import Repository


class UsersRepository(Repository):
    async def get_by_telegram_id(self, telegram_user_id: int) -> User | None:
        result = await self.session.execute(select(User).where(User.telegram_user_id == telegram_user_id))
        return result.scalar_one_or_none()

    async def get_or_create(self, telegram_user: TelegramUser) -> User:
        user = await self.get_by_telegram_id(telegram_user.id)
        if user is None:
            user = User(
                telegram_user_id=telegram_user.id,
                username=telegram_user.username,
                first_name=telegram_user.first_name,
                last_name=telegram_user.last_name,
            )
            self.session.add(user)
            await self.session.flush()
            return user

        user.username = telegram_user.username
        user.first_name = telegram_user.first_name
        user.last_name = telegram_user.last_name
        user.is_active = True
        await self.session.flush()
        return user

