from typing import Any

from app.store.bot.callbacks import CallbackBase
from app.store.tg_api.builders import MENU_TEXT


class BotRouter:
    def __init__(self):
        self.message_handlers = {}
        self.callback_handlers = {}

    def message(self, *command: str):
        def decorator(func):
            for cmd in command:
                self.message_handlers[cmd] = func
            return func
        return decorator

    def callback(self, trigger: Any):
        def decorator(func):
            if isinstance(trigger, type) and issubclass(trigger, CallbackBase):
                self.callback_handlers[trigger.prefix] = (func, trigger)
            else:
                self.callback_handlers[trigger] = (func, None)
            return func
        return decorator

    async def route_message(self, manager, chat_id: int, user_id: int, text: str):
        handler = self.message_handlers.get(text)
        if handler:
            await handler(manager, chat_id, user_id)
        else:
            await manager.app.store.tg_api.send_message(chat_id, MENU_TEXT)

    async def route_callback(self, manager, chat_id: int, message_id: int, user_id: int, data: str, callback_id: str):
        await manager.app.store.tg_api.answer_callback(callback_id)

        for prefix, (handler, cb_class) in self.callback_handlers.items():
            if data.startswith(prefix):
                parsed_data = cb_class(data) if cb_class else data
                await handler(manager, chat_id, message_id, parsed_data, user_id)
                return
