import asyncio

class Poller:
    def __init__(self, app):
        self.app = app
        self._task = None
    
    def start(self):
        self._task = asyncio.create_task(self._poll())
    
    async def stop(self):
        if self._task:
            self._task.cancel()
            await asyncio.gather(self._task, return_exceptions=True)
    
    async def _poll(self):
        offset = 0
        while True:
            updates = await self.app.store.tg_api.poll(offset)
            for update in updates:
                offset = update["update_id"] + 1
                await self.app.store.bot.handle_update(update)
            
            await asyncio.sleep(0.1)