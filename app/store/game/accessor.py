from typing import TYPE_CHECKING

from sqlalchemy import delete, select, update
from sqlalchemy.orm import selectinload

from app.store.game.models import GameAnsweredQuestionsModel, GameCategoriesModel, GameFinalBetsModel, GameModel, StatisticModel, UserModel
from app.store.quiz.models import CategoryModel

if TYPE_CHECKING:
    from app.store.store import Store


class GameAccessor:
    def __init__(self, store: "Store") -> None:
        self.store = store

    @property
    def _session(self):
        return self.store.app.database.sessionmaker

    async def create_game(self, chat_id: int, game_mode: str, game_type: str) -> GameModel:
        async with self._session() as session:
            game = GameModel(
                chat_id=chat_id,
                game_mode=game_mode,
                game_type=game_type,
                status="choosing_question",
            )
            session.add(game)
            await session.commit()
            return game

    async def get_active_game(self, chat_id: int) -> GameModel | None:
        async with self._session() as session:
            result = await session.execute(
                select(GameModel)
                .where(GameModel.chat_id == chat_id)
                .where(GameModel.status != "finished")
            )
            return result.scalar_one_or_none()

    async def update_game(self, game_id: int, **kwargs) -> None:
        async with self._session() as session:
            await session.execute(
                update(GameModel).where(GameModel.id == game_id).values(**kwargs)
            )
            await session.commit()

    async def add_player(self, user_id: int, game_id: int) -> None:
        async with self._session() as session:
            await session.execute(
                update(UserModel).where(UserModel.id == user_id).values(game_id=game_id, points=0)
            )
            await session.commit()

    async def get_players(self, game_id: int) -> list[UserModel]:
        async with self._session() as session:
            result = await session.execute(
                select(UserModel).where(UserModel.game_id == game_id)
            )
            return list(result.scalars().all())

    async def remove_player(self, user_id: int) -> None:
        """Detach user from current game (surrender)."""
        async with self._session() as session:
            await session.execute(
                update(UserModel).where(UserModel.id == user_id).values(game_id=None)
            )
            await session.commit()

    async def add_answered_question(self, game_id: int, question_id: int) -> None:
        async with self._session() as session:
            session.add(GameAnsweredQuestionsModel(game_id=game_id, question_id=question_id))
            await session.commit()

    async def get_answered_question_ids(self, game_id: int) -> set[int]:
        async with self._session() as session:
            result = await session.execute(
                select(GameAnsweredQuestionsModel.question_id)
                .where(GameAnsweredQuestionsModel.game_id == game_id)
            )
            return set(result.scalars().all())

    async def update_player_points(self, user_id: int, delta: int) -> int:
        """Add delta to user points, return new points value."""
        async with self._session() as session:
            result = await session.execute(
                select(UserModel).where(UserModel.id == user_id)
            )
            user = result.scalar_one_or_none()
            if user is None:
                return 0
            user.points += delta
            await session.commit()
            return user.points

    async def update_statistics(self, players: list[UserModel], winner_id: int, right_answers_by_user: dict[int, int]) -> None:
        """Update statistic table for all players after game ends."""
        async with self._session() as session:
            for player in players:
                result = await session.execute(
                    select(StatisticModel).where(StatisticModel.user_id == player.id)
                )
                stat = result.scalar_one_or_none()
                if stat is None:
                    stat = StatisticModel(user_id=player.id)
                    session.add(stat)

                stat.games_played += 1
                stat.right_answers += right_answers_by_user.get(player.id, 0)
                if player.points > stat.max_points:
                    stat.max_points = player.points
                if player.id == winner_id:
                    stat.wins += 1

            await session.commit()
    
    async def get_user_statistics(self, user_id: int) -> StatisticModel | None:
        async with self._session() as session:
            result = await session.execute(
                select(StatisticModel).where(StatisticModel.user_id == user_id)
            )
            return result.scalar_one_or_none()

    async def get_player_active_game(self, user_id: int) -> GameModel | None:
        """Return the active game the user is currently in (via user.game_id)."""
        async with self._session() as session:
            result = await session.execute(
                select(UserModel).where(UserModel.id == user_id)
            )
            user = result.scalar_one_or_none()
            if user is None or user.game_id is None:
                return None
            result = await session.execute(
                select(GameModel)
                .where(GameModel.id == user.game_id)
                .where(GameModel.status != "finished")
            )
            return result.scalar_one_or_none()

    async def create_final_bet(self, game_id: int, user_id: int) -> None:
        async with self._session() as session:
            session.add(GameFinalBetsModel(game_id=game_id, user_id=user_id, bet=None, is_ready=False))
            await session.commit()

    async def set_final_bet(self, game_id: int, user_id: int, bet: int) -> None:
        async with self._session() as session:
            await session.execute(
                update(GameFinalBetsModel)
                .where(GameFinalBetsModel.game_id == game_id)
                .where(GameFinalBetsModel.user_id == user_id)
                .values(bet=bet, is_ready=True)
            )
            await session.commit()

    async def get_final_bets(self, game_id: int) -> list[GameFinalBetsModel]:
        async with self._session() as session:
            result = await session.execute(
                select(GameFinalBetsModel).where(GameFinalBetsModel.game_id == game_id)
            )
            return list(result.scalars().all())

    async def get_final_bet(self, game_id: int, user_id: int) -> GameFinalBetsModel | None:
        async with self._session() as session:
            result = await session.execute(
                select(GameFinalBetsModel)
                .where(GameFinalBetsModel.game_id == game_id)
                .where(GameFinalBetsModel.user_id == user_id)
            )
            return result.scalar_one_or_none()
        
    async def set_game_categories(self, game_id: int, category_ids: list[int]) -> None:
        async with self._session() as session:
            await session.execute(
                delete(GameCategoriesModel).where(GameCategoriesModel.game_id == game_id)
            )

            for category_id in category_ids:
                game_category = GameCategoriesModel(game_id=game_id, category_id=category_id)
                session.add(game_category)
            await session.commit()

    async def get_game_categories(self, game_id: int) -> list[CategoryModel]:
        async with self._session() as session:
            result = await session.execute(
                select(CategoryModel)
                .options(selectinload(CategoryModel.questions))
                .join(GameCategoriesModel)
                .where(GameCategoriesModel.game_id == game_id)
            )
            return result.scalars().all()
        
    async def clear_game_categories(self, game_id: int) -> None:
        async with self._session() as session:
            await session.execute(
                delete(GameCategoriesModel).where(GameCategoriesModel.game_id == game_id)
            )
            await session.commit()