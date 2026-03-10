from enum import Enum

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

    surrender = "/surr"


CATEGORIES = [{"id": 1, "name": "🌍 География"},
            {"id": 2, "name": "🔬 Наука"},
            {"id": 3, "name": "🎬 Кино"},
            {"id": 4, "name": "🎵 Музыка"},
            {"id": 5, "name": "⚽ Спорт"},]

QUESTION_PRICES = [100, 200, 300, 400, 500]

class GameModes(Enum):
    STANDART = "standart"
    BLITZ = "blitz"

    @property
    def labels(self):
        labels = {
            GameModes.STANDART: "🕹 Обычный",
            GameModes.BLITZ: "⚡️ Быстрый"
        }

        return labels[self]