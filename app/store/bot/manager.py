from app.store.bot.handlers import handle_answer_message, router
from app.store.tg_api.schema import Update


class BotManager:
    def __init__(self, app):
        self.app = app
        self.router = router

    async def handle_update(self, update: dict):
        update = Update.model_validate(update)
        if update.message:
            message = update.message
            chat_id = message.chat.id
            text = message.text or ""
            user_id = message.from_user.id if message.from_user else None

            if user_id:
                await self.app.store.user.get_or_create_user(user_id)

            # Check if this message is an answer to an active question
            if user_id and await self._is_pending_answer(chat_id, user_id):
                await handle_answer_message(self, chat_id, user_id, text)
                return

            # During answering state, ignore messages from non-answerers
            if user_id and await self._is_game_answering(chat_id):
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
            and game.status == "answering"
            and game.choosing_user_id == user_id
        )

    async def _is_game_answering(self, chat_id: int) -> bool:
        """Return True if a game is active and waiting for an answer."""
        game = await self.app.store.game.get_active_game(chat_id)
        return game is not None and game.status == "answering"
