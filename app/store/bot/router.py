class BotRouter:
    def __init__(self):
        self.message_handlers = {}
        self.callback_handlers = {}
    
    def message(self, *command: str): # Через запятую строку можно будет обрабатывать команды с аргументами, например "/start arg1 arg2"
        def decorator(func):
            for cmd in command:
                self.message_handlers[cmd] = func
            return func
        return decorator
    
    def callback(self, prefix: str):
        def decorator(func):
            self.callback_handlers[prefix] = func
            return func
        return decorator
    
    async def route_message(self, manager, chat_id: int, text: str):
        handler = self.message_handlers.get(text)
        if handler:
            await handler(manager, chat_id)
        else:
            await manager.app.store.tg_api.send_message(
                chat_id, 
                "Не сдавайся, солнышко ☀️. Ты справишься, ты введёшь правильную команду🤗"
            )

    async def route_callback(self, manager, chat_id: int, message_id: int, data: str, callback_id: str):
        await manager.app.store.tg_api.answer_callback(callback_id)
        
        for prefix, handler in self.callback_handlers.items():
            if data.startswith(prefix):
                await handler(manager, chat_id, message_id, data)
                return
