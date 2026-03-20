from typing import TYPE_CHECKING

from sqlalchemy import select, update
from sqlalchemy.orm import selectinload

from app.store.game.models import GamePlayerModel, StatisticModel, UserModel

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
                user = UserModel(id=tg_id, username=username, first_name=first_name)
                session.add(user)
                await session.flush()
                statistic = StatisticModel(user_id=tg_id)
                session.add(statistic)
                await session.commit()
            else:
                if username is not None and (user.username != username or user.first_name != first_name):
                    user.username = username
                    user.first_name = first_name
                    await session.commit()
                elif username is None and first_name is not None and user.first_name != first_name:
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
        
    async def give_points(self, user_id, game_id):
        async with self._session() as session:
            await session.execute(
                update(GamePlayerModel)
                .where(GamePlayerModel.user_id == user_id)
                .where(GamePlayerModel.game_id == game_id)
                .values(points=GamePlayerModel.points + 10000)
            )

            await session.commit()

    async def increment_correct_answers(self, user_id: int):
        async with self._session() as session:
            await session.execute(
                update(StatisticModel)
                .where(StatisticModel.user_id == user_id)
                .values(right_answers=StatisticModel.right_answers + 1)
            )
            await session.commit()