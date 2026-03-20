# app/store/matchmaking/accessor.py
from typing import TYPE_CHECKING
from sqlalchemy import delete, select, update
from app.store.matchmaking.models import MatchmakingModel

if TYPE_CHECKING:
    from app.store.store import Store


class MatchmakingAccessor:
    def __init__(self, store: "Store") -> None:
        self.store = store

    @property
    def _session(self):
        return self.store.app.database.sessionmaker

    async def add_to_queue(self, user_id: int, game_mode: str) -> bool:
        """Добавить игрока в очередь с выбранным режимом. False если уже в очереди."""
        async with self._session() as session:
            existing = await session.execute(
                select(MatchmakingModel).where(MatchmakingModel.user_id == user_id)
            )
            if existing.scalar_one_or_none():
                return False
            session.add(MatchmakingModel(user_id=user_id, game_mode=game_mode))
            await session.commit()
            return True

    async def remove_from_queue(self, user_id: int) -> None:
        async with self._session() as session:
            await session.execute(
                delete(MatchmakingModel).where(MatchmakingModel.user_id == user_id)
            )
            await session.commit()

    async def get_queue(self, game_mode: str | None = None) -> list[MatchmakingModel]:
        """Вернуть очередь, опционально отфильтрованную по режиму."""
        async with self._session() as session:
            q = select(MatchmakingModel).order_by(MatchmakingModel.joined_at)
            if game_mode:
                q = q.where(MatchmakingModel.game_mode == game_mode)
            result = await session.execute(q)
            return list(result.scalars().all())

    async def is_in_queue(self, user_id: int) -> MatchmakingModel | None:
        """Вернуть запись игрока в очереди или None."""
        async with self._session() as session:
            result = await session.execute(
                select(MatchmakingModel).where(MatchmakingModel.user_id == user_id)
            )
            return result.scalar_one_or_none()

    async def remove_players(self, user_ids: list[int]) -> None:
        async with self._session() as session:
            await session.execute(
                delete(MatchmakingModel).where(MatchmakingModel.user_id.in_(user_ids))
            )
            await session.commit()

    async def set_search_message(self, user_id: int, message_id: int) -> None:
        async with self._session() as session:
            await session.execute(
                update(MatchmakingModel)
                .where(MatchmakingModel.user_id == user_id)
                .values(search_message_id=message_id)
            )
            await session.commit()
 
    async def get_queue_with_messages(self, game_mode: str) -> list[MatchmakingModel]:
        """Вернуть всех в очереди с их search_message_id."""
        async with self._session() as session:
            result = await session.execute(
                select(MatchmakingModel)
                .where(MatchmakingModel.game_mode == game_mode)
                .order_by(MatchmakingModel.joined_at)
            )
            return list(result.scalars().all())