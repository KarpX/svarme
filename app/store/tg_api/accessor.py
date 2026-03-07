from aiohttp import ClientSession
import aiohttp

class TgApiAccessor:
    def __init__(self, app):
        self.app = app
        self.session: ClientSession | None = None
    
    async def poll(self, offset: int = 0):
        url = f"https://api.telegram.org/bot{self.app.config.bot.token}/getUpdates"
        async with self.session.get(url, params={"offset": offset, "timeout":30}) as conn:
            data = await conn.json()
            return data.get("result", [])
    
    async def send_message(self, chat_id: int, text: str):
        url = f"https://api.telegram.org/bot{self.app.config.bot.token}/sendMessage"
        await self.session.post(url, json={"chat_id": chat_id, "text": text})

    async def connect(self):
        self.session = aiohttp.ClientSession()

    async def disconnect(self):
        if self.session:
            await self.session.close()