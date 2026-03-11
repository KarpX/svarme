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