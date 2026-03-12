from typing import TYPE_CHECKING

from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.store.game.models import StatisticModel, UserModel

if TYPE_CHECKING:
    from app.store.store import Store


class UserAccessor:
    def __init__(self, store: "Store") -> None:
        self.store = store

    @property
    def _session(self):
        return self.store.app.database.sessionmaker

    async def get_or_create_user(self, tg_id: int, username: str = None, first_name: str = None) -> UserModel:
        async with self._session() as session:
            result = await session.execute(
                select(UserModel)
                .options(selectinload(UserModel.statistic))
                .where(UserModel.id == tg_id)
            )
            user = result.scalar_one_or_none()
            if user is None:
                user = UserModel(id=tg_id)
                session.add(user)
                await session.flush()
                statistic = StatisticModel(user_id=tg_id)
                session.add(statistic)
                await session.commit()
            else:
                if username and (user.username != username or user.first_name != first_name):
                    user.username = username
                    user.first_name = first_name
                    await session.commit()
            return user

    async def get_user(self, tg_id: int) -> UserModel | None:
        async with self._session() as session:
            result = await session.execute(
                select(UserModel)
                .options(selectinload(UserModel.statistic))
                .where(UserModel.id == tg_id)
            )
            return result.scalar_one_or_none()
