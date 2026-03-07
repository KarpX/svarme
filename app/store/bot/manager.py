class BotManager:
    def __init__(self, app):
        self.app = app
    
    async def handle_update(self, update: dict):
        if "message" in update:
            message = update["message"]
            chat_id = message["chat"]["id"]
            text = message.get("text", "")

            if text:
                await self.app.store.tg_api.send_message(chat_id, text)