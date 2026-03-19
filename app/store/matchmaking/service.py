# app/store/matchmaking/service.py
import asyncio
import logging
import random
from datetime import datetime, timezone
from typing import TYPE_CHECKING

from app.store.tg_api.builders import GAME_BUTTONS
from app.store.tg_api.game_constants import GameStatus

if TYPE_CHECKING:
    from app.web.app import Application

MATCHMAKING_INTERVAL = 10
MATCHMAKING_MAX_WAIT = 20    # 3 минуты
MATCHMAKING_MIN_PLAYERS = 2
MATCHMAKING_MAX_PLAYERS = 4


def make_virtual_chat_id(game_id: int) -> int:
    return -(game_id * 1000 + 1)


class MatchmakingService:
    def __init__(self, app: "Application"):
        self.app = app
        self._task: asyncio.Task | None = None

    def start(self) -> None:
        self._task = asyncio.create_task(self._loop())
        logging.info("Matchmaking service started")

    async def stop(self) -> None:
        if self._task:
            self._task.cancel()
            await asyncio.gather(self._task, return_exceptions=True)

    async def _loop(self) -> None:
        while True:
            try:
                await asyncio.sleep(MATCHMAKING_INTERVAL)
                await self._tick()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logging.error(f"Matchmaking error: {e}", exc_info=True)

    async def _tick(self) -> None:
        from app.store.tg_api.game_constants import GameModes
        # Проверяем каждый режим отдельно
        for mode in GameModes:
            await self._check_mode(mode.value)

    async def _check_mode(self, game_mode: str) -> None:
        queue = await self.app.store.matchmaking.get_queue(game_mode=game_mode)
        # Обновляем сообщения поиска у всех в очереди актуальным количеством
        await self._update_search_messages(queue, game_mode)
        if len(queue) < MATCHMAKING_MIN_PLAYERS:
            return

        now = datetime.now(timezone.utc)
        candidates = queue[:MATCHMAKING_MAX_PLAYERS]

        # Полный состав — сразу запускаем
        if len(candidates) == MATCHMAKING_MAX_PLAYERS:
            await self._start_match(candidates, game_mode)
            return

        # Проверяем таймаут самого раннего игрока
        oldest = candidates[0]
        oldest_joined = (
            oldest.joined_at.replace(tzinfo=timezone.utc)
            if oldest.joined_at.tzinfo is None
            else oldest.joined_at
        )
        if (now - oldest_joined).total_seconds() >= MATCHMAKING_MAX_WAIT:
            await self._start_match(candidates, game_mode)

    async def _update_search_messages(self, queue, game_mode: str) -> None:
        """Редактировать сообщение поиска у каждого игрока в очереди."""
        from app.store.bot.handlers import _build_search_text
        from app.store.tg_api.game_constants import GameModes
        mode_label = next((m.labels for m in GameModes if m.value == game_mode), game_mode)
        text = _build_search_text(mode_label, len(queue))
        for entry in queue:
            if not entry.search_message_id:
                continue
            try:
                await self.app.store.tg_api.edit_message(
                    entry.user_id, entry.search_message_id, text, {"inline_keyboard": []}
                )
            except Exception:
                pass

    async def _start_match(self, candidates, game_mode: str) -> None:
        user_ids = [c.user_id for c in candidates]
        await self.app.store.matchmaking.remove_players(user_ids)

        # Создаём игру с виртуальным chat_id
        game = await self.app.store.game.create_game(
            chat_id=0, game_mode=game_mode, game_type="dm",
        )
        virtual_chat_id = make_virtual_chat_id(game.id)
        await self.app.store.game.update_game(game.id, chat_id=virtual_chat_id)

        for user_id in user_ids:
            await self.app.store.game.add_player(user_id, game.id)

        # Собираем имена
        player_names = []
        for user_id in user_ids:
            user = await self.app.store.user.get_user(user_id)
            player_names.append(user.display_name if user else f"ID:{user_id}")

        from app.store.tg_api.game_constants import GameModes
        mode_label = next(
            (m.labels for m in GameModes if m.value == game_mode), game_mode
        )
        names_text = ", ".join(player_names)

        for user_id in user_ids:
            from app.store.tg_api.builders import SEARCHING_BUTTONS, GAME_START_TEXT
            # await self.app.store.tg_api.send_message(
            #     user_id,
            #     f"🎮 <b>Матч найден!</b> Режим: {mode_label}\n\n"
            #     f"Игроки: {names_text}\n\n"
            #     f"Игра начинается!",
            # )
            await self.app.store.tg_api.send_keyboard(user_id, GAME_BUTTONS, f"🎮 <b>Матч найден!</b> Режим: {mode_label}\n\n"
                f"Игроки: {names_text}\n\n"
                f"Игра начинается!")

        # Запускаем игру
        first_chooser = random.choice(user_ids)
        await self.app.store.game.update_game(
            game.id,
            status=GameStatus.CHOOSING_QUESTION.value,
            choosing_user_id=first_chooser,
        )
        self.app.store.bot.schedule_choose_timer(game.id, virtual_chat_id)

        # Отправляем объявление и доску категорий каждому игроку
        from app.store.bot.handlers import _announce_chooser, _send_category_board
        await _announce_chooser(self.app.store.bot, virtual_chat_id, first_chooser)
        await _send_category_board(self.app.store.bot, virtual_chat_id)

        logging.info(f"Matchmaking: game {game.id} started, mode={game_mode}, players={user_ids}")