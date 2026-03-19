from typing import TYPE_CHECKING

from sqlalchemy import delete, select, update
from sqlalchemy.orm import selectinload

from app.store.game.models import (
    GameAnsweredQuestionsModel,
    GameCategoriesModel,
    GameFinalAnswerModel,
    GameFinalBetsModel,
    GameFinalRemovedCategoryModel,
    GameFinishVoteModel,
    GameModel,
    GamePlayerModel,
    LobbyMessageModel,
    StatisticModel,
    UserModel,
)
from app.store.quiz.models import CategoryModel, QuestionModel
from app.web import logger

if TYPE_CHECKING:
    from app.store.store import Store


class GameAccessor:
    def __init__(self, store: "Store") -> None:
        self.store = store

    @property
    def _session(self):
        return self.store.app.database.sessionmaker

    # ── Game CRUD ──────────────────────────────────────────────────────────

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
                .where(GameModel.status.notin_(["finished", "waiting", "pending"]))
            )
            return result.scalar_one_or_none()

    async def get_all_active_games(self) -> list[GameModel]:
        async with self._session() as session:
            result = await session.execute(
                select(GameModel)
                .where(GameModel.status.notin_(["finished", "waiting", "pending"]))
            )
            return list(result.scalars().all())
        
    async def get_all_games_list(self) -> list[GameModel] | None:
        async with self._session() as session:
            result = await session.execute(
                select(GameModel).where(GameModel.status.not_like("finished"))
            )
            return list(result.scalars().all())
        
    async def get_game_by_id(self, game_id) -> GameModel | None:
        async with self._session() as session:
            result = await session.execute(
                select(GameModel).where(GameModel.id == game_id)
            )
            return result.scalar_one_or_none()

    async def update_game(self, game_id: int, **kwargs) -> None:
        async with self._session() as session:
            await session.execute(
                update(GameModel).where(GameModel.id == game_id).values(**kwargs)
            )
            await session.commit()

    async def delete_active_games(self, game_id: int | None = None) -> None:
        async with self._session() as session:
            query = delete(GameModel).where(GameModel.status.notin_(["finished", "waiting", "pending"]))

            if game_id is not None:
                query = query.where(GameModel.id == game_id)

            await session.execute(query)
            await session.commit()

    # ── Players (game_players table) ───────────────────────────────────────

    async def add_player(self, user_id: int, game_id: int) -> None:
        """Добавить игрока в игру (создать запись в game_players)."""
        async with self._session() as session:
            # Не дублировать, если уже есть
            existing = await session.execute(
                select(GamePlayerModel)
                .where(GamePlayerModel.game_id == game_id)
                .where(GamePlayerModel.user_id == user_id)
            )
            if existing.scalar_one_or_none():
                return
            session.add(GamePlayerModel(game_id=game_id, user_id=user_id, points=0))
            await session.commit()

    async def get_players(self, game_id: int) -> list[GamePlayerModel]:
        """Вернуть список GamePlayerModel для игры."""
        async with self._session() as session:
            result = await session.execute(
                select(GamePlayerModel).where(GamePlayerModel.game_id == game_id)
            )
            return list(result.scalars().all())

    async def is_player(self, game_id: int, user_id: int) -> bool:
        async with self._session() as session:
            result = await session.execute(
                select(GamePlayerModel.id).where(
                    GamePlayerModel.game_id == game_id,
                    GamePlayerModel.user_id == user_id,
                )
            )
            return result.scalar_one_or_none() is not None

    async def remove_player(self, game_id: int, user_id: int) -> None:
        """Удалить игрока из конкретной игры."""
        async with self._session() as session:
            await session.execute(
                delete(GamePlayerModel)
                .where(GamePlayerModel.game_id == game_id)
                .where(GamePlayerModel.user_id == user_id)
            )
            await session.commit()

    async def update_player_points(self, game_id: int, user_id: int, delta: int) -> int:
        """Изменить очки игрока в конкретной игре, вернуть новое значение."""
        async with self._session() as session:
            result = await session.execute(
                select(GamePlayerModel)
                .where(GamePlayerModel.game_id == game_id)
                .where(GamePlayerModel.user_id == user_id)
            )
            player = result.scalar_one_or_none()
            if player is None:
                return 0
            player.points += delta
            await session.commit()
            return player.points

    async def get_player(self, game_id: int, user_id: int) -> GamePlayerModel | None:
        """Получить запись игрока в конкретной игре."""
        async with self._session() as session:
            result = await session.execute(
                select(GamePlayerModel)
                .where(GamePlayerModel.game_id == game_id)
                .where(GamePlayerModel.user_id == user_id)
            )
            return result.scalar_one_or_none()

    async def get_player_active_game(self, user_id: int) -> GameModel | None:
        """
        Вернуть активную игру (не лобби, не finished), в которой участвует пользователь.
        Нужно для финальных раундов (DM-ставки и ответы).
        """
        async with self._session() as session:
            result = await session.execute(
                select(GameModel)
                .join(GamePlayerModel, GamePlayerModel.game_id == GameModel.id)
                .where(GamePlayerModel.user_id == user_id)
                .where(GameModel.status.notin_(["finished", "waiting", "pending"]))
            )
            return result.scalar_one_or_none()

    # ── Statistics ─────────────────────────────────────────────────────────

    async def update_statistics(self, players: list[GamePlayerModel], winner_id: int) -> None:
        """Обновить статистику после окончания игры."""
        async with self._session() as session:
            for player in players:
                result = await session.execute(
                    select(StatisticModel).where(StatisticModel.user_id == player.user_id)
                )
                stat = result.scalar_one_or_none()
                if stat is None:
                    stat = StatisticModel(user_id=player.user_id)
                    session.add(stat)

                stat.games_played += 1
                if player.points > stat.max_points:
                    stat.max_points = player.points
                if player.user_id == winner_id:
                    stat.wins += 1

            await session.commit()

    async def get_user_statistics(self, user_id: int) -> StatisticModel | None:
        async with self._session() as session:
            result = await session.execute(
                select(StatisticModel).where(StatisticModel.user_id == user_id)
            )
            return result.scalar_one_or_none()

    # ── Answered questions ─────────────────────────────────────────────────

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

    # ── Categories ─────────────────────────────────────────────────────────

    async def set_game_categories(self, game_id: int, category_ids: list[int]) -> None:
        async with self._session() as session:
            await session.execute(
                delete(GameCategoriesModel).where(GameCategoriesModel.game_id == game_id)
            )
            for category_id in category_ids:
                session.add(GameCategoriesModel(game_id=game_id, category_id=category_id))
            await session.commit()

    async def get_game_categories(self, game_id: int) -> list[CategoryModel]:
        async with self._session() as session:
            result = await session.execute(
                select(CategoryModel)
                .options(selectinload(CategoryModel.questions).joinedload(QuestionModel.category))
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

    # ── Lobby (waiting / pending) ──────────────────────────────────────────

    async def get_lobby_game(self, chat_id: int) -> GameModel | None:
        async with self._session() as session:
            result = await session.execute(
                select(GameModel)
                .where(GameModel.chat_id == chat_id)
                .where(GameModel.status.in_(["waiting", "pending"]))
            )
            return result.scalar_one_or_none()

    async def create_lobby(self, chat_id: int, user_id: int) -> GameModel:
        async with self._session() as session:
            game = GameModel(
                chat_id=chat_id,
                game_mode="",
                game_type="group",
                status="waiting",
                choosing_user_id=user_id,
            )
            session.add(game)
            await session.commit()
            return game

    async def get_lobby_players(self, chat_id: int) -> list[UserModel]:
        """Вернуть UserModel игроков, которые сейчас в лобби данного чата."""
        async with self._session() as session:
            result = await session.execute(
                select(UserModel)
                .join(GamePlayerModel, GamePlayerModel.user_id == UserModel.id)
                .join(GameModel, GamePlayerModel.game_id == GameModel.id)
                .where(GameModel.chat_id == chat_id)
                .where(GameModel.status.in_(["waiting", "pending"]))
            )
            return list(result.scalars().all())

    async def add_lobby_player(self, chat_id: int, user_id: int) -> GameModel:
        """Добавить игрока в лобби, создав его при необходимости."""
        game = await self.get_lobby_game(chat_id)
        if not game:
            game = await self.create_lobby(chat_id, user_id)
        await self.add_player(user_id, game.id)
        return game

    async def remove_lobby_player(self, chat_id: int, user_id: int) -> None:
        """Убрать игрока из лобби."""
        async with self._session() as session:
            game = await self.get_lobby_game(chat_id)
            if not game:
                return

            # Сначала ищем следующего владельца (ДО удаления игрока из сессии)
            next_admin = None
            if game.choosing_user_id == user_id:
                result = await session.execute(
                    select(GamePlayerModel.user_id)
                    .where(GamePlayerModel.game_id == game.id)
                    .where(GamePlayerModel.user_id != user_id)
                )
                next_admin = result.scalars().first()

            # Теперь удаляем игрока
            await session.execute(
                delete(GamePlayerModel)
                .where(GamePlayerModel.game_id == game.id)
                .where(GamePlayerModel.user_id == user_id)
            )

            # Обновляем или удаляем лобби
            if game.choosing_user_id == user_id:
                if next_admin:
                    await session.execute(
                        update(GameModel)
                        .where(GameModel.id == game.id)
                        .values(choosing_user_id=next_admin)
                    )
                else:
                    # Лобби пустое — удалить игру (cascade удалит lobby_messages и game_players)
                    await session.execute(
                        delete(GameModel).where(GameModel.id == game.id)
                    )

            await session.commit()

    # ── Lobby messages ─────────────────────────────────────────────────────

    async def add_lobby_message(self, game_id: int, message_id: int):
        if not message_id:
            return
        async with self._session() as session:
            exists = await session.execute(
                select(LobbyMessageModel).where(
                    LobbyMessageModel.game_id == game_id,
                    LobbyMessageModel.message_id == message_id,
                )
            )
            if not exists.scalar():
                session.add(LobbyMessageModel(game_id=game_id, message_id=message_id))
                await session.commit()

    async def get_lobby_message(self, game_id: int) -> int | None:
        async with self._session() as session:
            result = await session.execute(
                select(LobbyMessageModel.message_id)
                .where(LobbyMessageModel.game_id == game_id)
            )
            return result.scalar_one_or_none()

    async def clear_lobby_message(self, game_id: int):
        async with self._session() as session:
            await session.execute(
                delete(LobbyMessageModel).where(LobbyMessageModel.game_id == game_id)
            )
            await session.commit()

    # ── Final round ────────────────────────────────────────────────────────

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

    async def add_final_removed_category(self, game_id: int, category_id: int) -> None:
        async with self._session() as session:
            session.add(GameFinalRemovedCategoryModel(game_id=game_id, category_id=category_id))
            await session.commit()

    async def get_final_removed_category_ids(self, game_id: int) -> set[int]:
        async with self._session() as session:
            result = await session.execute(
                select(GameFinalRemovedCategoryModel.category_id)
                .where(GameFinalRemovedCategoryModel.game_id == game_id)
            )
            return set(result.scalars().all())

    async def set_final_answer(self, game_id: int, user_id: int, answer: str) -> None:
        async with self._session() as session:
            session.add(GameFinalAnswerModel(game_id=game_id, user_id=user_id, answer=answer))
            await session.commit()

    async def get_final_answers(self, game_id: int) -> list[GameFinalAnswerModel]:
        async with self._session() as session:
            result = await session.execute(
                select(GameFinalAnswerModel).where(GameFinalAnswerModel.game_id == game_id)
            )
            return list(result.scalars().all())

    async def get_final_answer(self, game_id: int, user_id: int) -> GameFinalAnswerModel | None:
        async with self._session() as session:
            result = await session.execute(
                select(GameFinalAnswerModel)
                .where(GameFinalAnswerModel.game_id == game_id)
                .where(GameFinalAnswerModel.user_id == user_id)
            )
            return result.scalar_one_or_none()

    # ── Finish votes ───────────────────────────────────────────────────────

    async def add_finish_vote(self, game_id: int, user_id: int) -> None:
        async with self._session() as session:
            session.add(GameFinishVoteModel(game_id=game_id, user_id=user_id))
            await session.commit()

    async def has_finish_vote(self, game_id: int, user_id: int) -> bool:
        async with self._session() as session:
            result = await session.execute(
                select(GameFinishVoteModel)
                .where(GameFinishVoteModel.game_id == game_id)
                .where(GameFinishVoteModel.user_id == user_id)
            )
            return result.scalar_one_or_none() is not None

    async def count_finish_votes(self, game_id: int) -> int:
        async with self._session() as session:
            result = await session.execute(
                select(GameFinishVoteModel).where(GameFinishVoteModel.game_id == game_id)
            )
            return len(result.scalars().all())

    async def clear_finish_votes(self, game_id: int) -> None:
        async with self._session() as session:
            await session.execute(
                delete(GameFinishVoteModel).where(GameFinishVoteModel.game_id == game_id)
            )
            await session.commit()

    # ── Admin ──────────────────────────────────────────────────────────────

    async def skip_current_round_questions(self, game_id: int):
        async with self._session() as session:
            categories = await self.get_game_categories(game_id)
            for cat in categories:
                for q in cat.questions:
                    exists = await session.execute(
                        select(GameAnsweredQuestionsModel).where(
                            GameAnsweredQuestionsModel.game_id == game_id,
                            GameAnsweredQuestionsModel.question_id == q.id,
                        )
                    )
                    if not exists.scalar():
                        session.add(GameAnsweredQuestionsModel(game_id=game_id, question_id=q.id))

            await session.execute(
                delete(GameCategoriesModel).where(GameCategoriesModel.game_id == game_id)
            )
            await session.commit()