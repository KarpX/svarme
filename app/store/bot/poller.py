import asyncio
import logging

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
            try:
                updates = await self.app.store.tg_api.poll(offset)
                for update in updates:
                    offset = update["update_id"] + 1

                    try:
                        await self.app.store.bot.handle_update(update)
                    except Exception as e:
                        logging.error(f"Error handling update: {e}")
            except Exception as e:
                logging.error(f"Error polling Telegram API: {e}")
                await asyncio.sleep(5)
                continue
            await asyncio.sleep(0.1)