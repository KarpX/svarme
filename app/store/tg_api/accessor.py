import json

from aiohttp import ClientSession
import aiohttp
from app.store.tg_api.game_constants import BotButtons, BotCommands


class TgApiAccessor:
    def __init__(self, app):
        self.app = app
        self.session: ClientSession | None = None
        self.build_url = f"https://api.telegram.org/bot{self.app.config.bot.token}"
    
    async def poll(self, offset: int = 0):
        url = f"{self.build_url}/getUpdates"
        async with self.session.get(url, params={"offset": offset, "timeout":30}) as conn:
            data = await conn.json()
            return data.get("result", [])
    
    async def send_message(self, chat_id: int, text: str):
        url = f"{self.build_url}/sendMessage"
        async with self.session.post(url, json={"chat_id": chat_id, "text": text, "parse_mode" : "HTML"}) as resp:
            return await resp.json()

    async def send_keyboard(self, chat_id: int, buttons: list, text, resize_keyboard=True, one_time_keyboard=False):
        url = f"{self.build_url}/sendMessage"

        keyboard = {
            "keyboard": buttons,
            "resize_keyboard": resize_keyboard, 
            "one_time_keyboard": one_time_keyboard
        }

        payload = {
            "chat_id": chat_id,
            "text" : text,
            "reply_markup": json.dumps(keyboard)
        }

        await self.session.post(url, json=payload)

    async def send_inline_keyboard(self, chat_id: int, text: str, keyboard: dict):
        url = f"{self.build_url}/sendMessage"
        payload = {
            "chat_id": chat_id,
            "text": text,
            "reply_markup": json.dumps(keyboard),
            "parse_mode": "HTML",
        }
        async with self.session.post(url, json=payload) as resp:
            return await resp.json()

    async def edit_message(self, chat_id: int, message_id: int, text: str, keyboard: dict):
        url = f"{self.build_url}/editMessageText"
        payload = {
            "chat_id": chat_id,
            "message_id": message_id,
            "text": text,
            "reply_markup": json.dumps(keyboard),
            "parse_mode": "HTML",
        }
        await self.session.post(url, json=payload)

    async def delete_message(self, chat_id: int, message_id: int):
        url = f"{self.build_url}/deleteMessage"
        await self.session.post(url, json={"chat_id": chat_id, "message_id": message_id})

    async def pin_chat_message(self, chat_id: int, message_id: int, disable_notification: bool = True):
        url = f"{self.build_url}/pinChatMessage"
        payload = {
            "chat_id" : chat_id,
            "message_id" : message_id,
            "disable_notification" : disable_notification
        }
        async with self.session.post(url, data=payload) as resp:
            return await resp.json()
        
    async def unpin_chat_message(self, chat_id: int, message_id: int):
        url = f"{self.build_url}/unpinChatMessage"
        payload = {
            "chat_id": chat_id,
            "message_id": message_id
        }
        async with self.session.post(url, json=payload) as resp:
            return await resp.json()

    async def answer_callback(self, callback_id: str):
        url = f"{self.build_url}/answerCallbackQuery"
        payload = {"callback_query_id": callback_id}
        await self.session.post(url, json=payload)

    async def connect(self):
        self.session = aiohttp.ClientSession()

    async def disconnect(self):
        if self.session:
            await self.session.close()