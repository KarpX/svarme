import json

from aiohttp import ClientSession
import aiohttp


class BotButtons:
    start_game = "🚀 Начать игру"
    statistics = "🏆 Статистика"
    rules = "📜 Правила"
    menu = "☰ Меню"

    surrender = "🏳️ Сдаться"


class BotCommands:
    start_game = "/game"
    rules = "/rules"
    stats = "/stats"
    menu = "/menu"


CATEGORIES = [
    {"id": 1, "name": "🌍 География"},
    {"id": 2, "name": "🔬 Наука"},
    {"id": 3, "name": "🎬 Кино"},
    {"id": 4, "name": "🎵 Музыка"},
    {"id": 5, "name": "⚽ Спорт"},
]

QUESTION_PRICES = [100, 200, 300, 400, 500]

GAME_MODES = [
    {"game_mode" : "standart", "name" : "🕹 Обычный"},
    {"game_mode" : "blitz", "name" : "⚡️ Быстрый"}]

def build_game_mode_keyboard() -> dict:
    row = []
    for mode in GAME_MODES:
        row.append({
            "text": mode["name"], "callback_data": f"gm:{mode['game_mode']}"
        })
    print(row)
    return {"inline_keyboard": [row]}

def build_category_keyboard() -> dict:
    rows = []
    for i in range(0, len(CATEGORIES), 2):
        row = [
            {"text": c["name"], "callback_data": f"cat:{c['id']}"}
            for c in CATEGORIES[i : i + 2]
        ]
        rows.append(row)
    return {"inline_keyboard": rows}


def build_question_keyboard(category_id: int) -> dict:
    rows = []
    row = []
    for price in QUESTION_PRICES:
        row.append({"text": str(price), "callback_data": f"q:{category_id}:{price}"})
        if len(row) == 3:
            rows.append(row)
            row = []
    if row:
        rows.append(row)
    rows.append([{"text": "← Назад", "callback_data": "back"}])
    return {"inline_keyboard": rows}


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
        await self.session.post(url, json={"chat_id": chat_id, "text": text, "parse_mode" : "HTML"})

    async def send_start_menu(self, chat_id: int):
        url = f"https://api.telegram.org/bot{self.app.config.bot.token}/sendMessage"
        
        keyboard = {
            "keyboard": [
                [{"text": BotButtons.start_game}, {"text": BotButtons.statistics}],
                [{"text": BotButtons.rules}, {"text" : BotButtons.menu}]
            ],
            "resize_keyboard": True, 
            "one_time_keyboard": False
        }

        payload = {
            "chat_id": chat_id,
            "text": "🏠 Меню"
            "\n\n 🗺 Основная навигация"
            f"\n{BotCommands.start_game} – 🚀 Начать игру"
            f"\n{BotCommands.stats} – 🏆 Статистика"
            f"\n{BotCommands.rules} – 📜 Правила",
            "reply_markup": json.dumps(keyboard)
        }

        await self.session.post(url, json=payload)

    async def send_game_menu(self, chat_id: int):
        url = f"https://api.telegram.org/bot{self.app.config.bot.token}/sendMessage"

        keyboard = {
            "keyboard": [
                [{"text": BotButtons.rules}, {"text" : BotButtons.menu}],
                [{"text" : BotButtons.surrender} ]
            ],
            "resize_keyboard": True, 
            "one_time_keyboard": False
        }

        payload = {
            "chat_id": chat_id,
            "text" : "Игра началась!",
            "reply_markup": json.dumps(keyboard)
        }

        await self.session.post(url, json=payload)

    async def send_game_mode_choose_keyboard(self, chat_id: int):
        url = f"https://api.telegram.org/bot{self.app.config.bot.token}/sendMessage"
        payload = {
            "chat_id": chat_id,
            "text": "🕹 Выберите режим игры:",
            "reply_markup": json.dumps(build_game_mode_keyboard()),
            "parse_mode": "HTML",
        }
        await self.session.post(url, json=payload)

    async def send_category_keyboard(self, chat_id: int):
        url = f"https://api.telegram.org/bot{self.app.config.bot.token}/sendMessage"
        payload = {
            "chat_id": chat_id,
            "text": "📋 Выберите категорию:",
            "reply_markup": json.dumps(build_category_keyboard()),
            "parse_mode": "HTML",
        }
        await self.session.post(url, json=payload)

    async def edit_message(self, chat_id: int, message_id: int, text: str, keyboard: dict):
        url = f"https://api.telegram.org/bot{self.app.config.bot.token}/editMessageText"
        payload = {
            "chat_id": chat_id,
            "message_id": message_id,
            "text": text,
            "reply_markup": json.dumps(keyboard),
            "parse_mode": "HTML",
        }
        await self.session.post(url, json=payload)

    async def delete_message(self, chat_id: int, message_id: int):
        url = f"https://api.telegram.org/bot{self.app.config.bot.token}/deleteMessage"
        await self.session.post(url, json={"chat_id": chat_id, "message_id": message_id})

    async def answer_callback(self, callback_id: str):
        url = f"https://api.telegram.org/bot{self.app.config.bot.token}/answerCallbackQuery"
        payload = {"callback_query_id": callback_id}
        await self.session.post(url, json=payload)

    async def connect(self):
        self.session = aiohttp.ClientSession()

    async def disconnect(self):
        if self.session:
            await self.session.close()