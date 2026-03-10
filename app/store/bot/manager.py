from app.store.tg_api.builers import GAME_BUTTONS, GAME_START_TEXT, MENU_BUTTONS, MENU_TEXT, RULES_TEXT, build_category_keyboard, build_question_keyboard
from app.store.bot.handlers import router

class BotManager:
    def __init__(self, app):
        self.app = app
        self.router = router

    async def handle_update(self, update: dict):
        if "message" in update:
            message = update["message"]
            chat_id = message["chat"]["id"]
            text = message.get("text", "")

            await self.router.route_message(self, chat_id, text)

        elif "callback_query" in update:
            callback = update["callback_query"]
            chat_id = callback["message"]["chat"]["id"]
            message_id = callback["message"]["message_id"]
            data = callback["data"]

            await self.router.route_callback(self, chat_id, message_id, data, callback["id"])