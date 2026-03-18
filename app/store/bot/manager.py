import asyncio

from app.store.bot.handlers import (
    handle_answer_message,
    handle_cat_in_bag_answer,
    handle_final_answer_message,
    handle_final_bet_message,
    router,
    _on_choose_timeout,
    _on_answer_button_timeout,
    _on_answering_timeout,
)
from app.store.tg_api.game_constants import BotButtons, ChatType, GameStatus, GameTimers
from app.store.tg_api.schema import Update
from app.web import logger


class BotManager:
    def __init__(self, app):
        self.app = app
        self.router = router
        # game_id -> asyncio.Task
        self._timers: dict[int, asyncio.Task] = {}

    # ── timer helpers ──────────────────────────────────────────────

    async def restore_timers(self):
        from datetime import datetime, timezone
        active_games = await self.app.store.game.get_all_active_games()

        for game in active_games:
            game_id = game.id
            chat_id = game.chat_id
            now = datetime.now(timezone.utc)

            if game.status == GameStatus.CHOOSING_QUESTION.value:
                # No question_asked_at for choosing phase — just start fresh timer
                self.schedule_choose_timer(game_id, chat_id)

            elif game.status == GameStatus.ANSWERING.value:
                if game.choosing_user_id is None:
                    # Answer button is shown, nobody pressed it yet
                    if game.question_asked_at:
                        elapsed = (now - game.question_asked_at.replace(tzinfo=timezone.utc)
                                   if game.question_asked_at.tzinfo is None
                                   else now - game.question_asked_at).total_seconds()
                        seconds_left = max(GameTimers.ANSWER_TIMEOUT.value - elapsed, 5.0)
                    else:
                        seconds_left = GameTimers.ANSWER_TIMEOUT.value
                    self._timers[game_id] = asyncio.create_task(
                        _on_answer_button_timeout(self, game_id, chat_id, seconds_left)
                    )
                else:
                    # Someone is answering
                    if game.remaining_seconds is not None:
                        seconds_left = max(float(game.remaining_seconds), 5.0)
                    elif game.question_asked_at:
                        asked_at = (game.question_asked_at.replace(tzinfo=timezone.utc)
                                    if game.question_asked_at.tzinfo is None
                                    else game.question_asked_at)
                        elapsed = (now - asked_at).total_seconds()
                        seconds_left = max(GameTimers.ANSWERING_TIMEOUT.value - elapsed, 5.0)
                    else:
                        seconds_left = GameTimers.ANSWERING_TIMEOUT.value
                    self.schedule_answering_timer(game_id, chat_id, seconds_left)
                    
            elif game.status == GameStatus.CAT_IN_BAG.value:
                # target_user_id обязан ответить — восстанавливаем таймер на ввод ответа
                if game.remaining_seconds is not None:
                    seconds_left = max(float(game.remaining_seconds), 5.0)
                elif game.question_asked_at:
                    asked_at = (game.question_asked_at.replace(tzinfo=timezone.utc)
                                if game.question_asked_at.tzinfo is None
                                else game.question_asked_at)
                    elapsed = (now - asked_at).total_seconds()
                    seconds_left = max(GameTimers.ANSWERING_TIMEOUT.value - elapsed, 5.0)
                else:
                    seconds_left = GameTimers.ANSWERING_TIMEOUT.value
                self.schedule_answering_timer(game_id, chat_id, seconds_left)

    def cancel_timer(self, game_id: int) -> None:
        task = self._timers.pop(game_id, None)
        if task and not task.done():
            current = asyncio.current_task()
            if task is not current:
                task.cancel()

    def schedule_choose_timer(self, game_id: int, chat_id: int) -> None:
        self.cancel_timer(game_id)
        logger.logging.info("Choose timer scheduled")
        self._timers[game_id] = asyncio.create_task(
            _on_choose_timeout(self, game_id, chat_id, GameTimers.CHOOSE_TIMEOUT.value)
        )

    def schedule_answer_button_timer(self, game_id: int, chat_id: int, seconds: float = None) -> None:
        self.cancel_timer(game_id)

        delay = seconds if seconds is not None else GameTimers.ANSWER_TIMEOUT.value

        if delay <= 0:
            delay = 0
        self._timers[game_id] = asyncio.create_task(
            _on_answer_button_timeout(self, game_id, chat_id, delay)
        )

    def schedule_answering_timer(
        self, game_id: int, chat_id: int, seconds_left: float = GameTimers.ANSWERING_TIMEOUT.value
    ) -> None:
        self.cancel_timer(game_id)
        self._timers[game_id] = asyncio.create_task(
            _on_answering_timeout(self, game_id, chat_id, seconds_left)
        )

    async def _is_cat_in_bag_target(self, chat_id: int, user_id: int) -> bool:
        """Return True if the game is in cat_in_bag state and this user is the target."""
        game = await self.app.store.game.get_active_game(chat_id)
        return (
            game is not None
            and game.status == GameStatus.CAT_IN_BAG.value
            and game.target_user_id == user_id
        )
    
    async def _is_cat_in_bag(self, chat_id: int) -> bool:
        """Return True if a game is active and in cat_in_bag state (including choosing)."""
        game = await self.app.store.game.get_active_game(chat_id)
        return game is not None and game.status in (
            GameStatus.CAT_IN_BAG.value,
            GameStatus.CAT_IN_BAG_CHOOSING.value,
        )

    async def handle_update(self, update: dict):
        update = Update.model_validate(update)
        if update.message:
            message = update.message
            chat_id = message.chat.id
            text = message.text or ""
            from_user = message.from_user
            user_id = from_user.id if message.from_user else None

            is_menu_button = text in [BotButtons.start_game, 
            BotButtons.menu, BotButtons.rules, BotButtons.statistics, 
            BotButtons.surrender, BotButtons.finish_game,
            BotButtons.exit_lobby]

            if user_id:
                await self.app.store.user.get_or_create_user(user_id, from_user.username, from_user.first_name)

            if (
                text == "/start"
                and user_id
                and message.chat.type == ChatType.PRIVATE.value
            ):
                game = await self.app.store.game.get_player_active_game(user_id)
                if game and game.status == GameStatus.FINAL_BETTING.value:
                    player = await self.app.store.game.get_player(game.id, user_id)
                    points = player.points if player else 0
                    await self.app.store.tg_api.send_message(
                        user_id,
                        f"🏁 <b>Финальный раунд!</b>\n"
                        f"Ваши очки: <b>{points}</b>\n\n"
                        f"Введите вашу ставку (от 1 до {points}):"
                    )
                    return

            if text.startswith("/") or is_menu_button:
                await self.router.route_message(self, chat_id, user_id or 0, text)
                return
            
            if user_id and await self._is_cat_in_bag_target(chat_id, user_id):
                await handle_cat_in_bag_answer(self, chat_id, user_id, text)
                return

            # Check if this message is an answer to an active question
            if user_id and await self._is_pending_answer(chat_id, user_id):
                await handle_answer_message(self, chat_id, user_id, text)
                return
            
            if user_id and await self._is_cat_in_bag(chat_id):
                return

            # During answering state, ignore messages from non-answerers
            if user_id and await self._is_game_answering(chat_id):
                return

            # Handle final round DM messages (betting / answering)
            if user_id and message.chat.type == ChatType.PRIVATE.value:
                game = await self.app.store.game.get_player_active_game(user_id)

                if game and game.status == GameStatus.FINAL_BETTING.value:
                    await handle_final_bet_message(self, user_id, text)
                    return
                if game and game.status == GameStatus.FINAL_ANSWERING.value:
                    await handle_final_answer_message(self, user_id, text, game)
                    return
                
            if user_id and message.chat.type != ChatType.PRIVATE.value:
                if await self._is_pending_answer(chat_id, user_id):
                    await handle_answer_message(self, chat_id, user_id, text)
                    return

                if await self._is_game_answering(chat_id):
                    return
                
            if message.chat.type != ChatType.PRIVATE.value:
                return

            await self.router.route_message(self, chat_id, user_id or 0, text)

        elif update.callback_query:
            callback = update.callback_query
            chat_id = callback.message.chat.id
            message_id = callback.message.message_id
            user_id = callback.from_user.id
            data = callback.data

            await self.app.store.user.get_or_create_user(user_id)
            await self.router.route_callback(self, chat_id, message_id, user_id, data, callback.id)

    async def _is_pending_answer(self, chat_id: int, user_id: int) -> bool:
        """Return True if the game is in 'answering' state and this user was locked in to answer."""
        game = await self.app.store.game.get_active_game(chat_id)
        return (
            game is not None
            and game.status == GameStatus.ANSWERING.value
            and game.choosing_user_id == user_id
        )

    async def _is_game_answering(self, chat_id: int) -> bool:
        """Return True if a game is active and waiting for an answer."""
        game = await self.app.store.game.get_active_game(chat_id)
        return game is not None and game.status == GameStatus.ANSWERING.value