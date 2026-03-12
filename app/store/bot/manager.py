from app.store.bot.handlers import router

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

            await self.router.route_message(self, chat_id, text)

        elif update.callback_query:
            callback = update.callback_query
            chat_id = callback.message.chat.id
            message_id = callback.message.message_id
            data = callback.data

            await self.router.route_callback(self, chat_id, message_id, data, callback.id)