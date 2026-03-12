from enum import Enum

class BotButtons:
    start_game = "🚀 Начать игру"
    statistics = "🏆 Статистика"
    rules = "📜 Правила"
    menu = "☰ Меню"

    surrender = "🏳️ Сдаться"
    finish_game = "🏁 Закончить игру"


class BotCommands:
    start_game = "/game"
    rules = "/rules"
    stats = "/stats"
    menu = "/menu"

    surrender = "/surr"
    finish_game = "/finish"

SURR_FACES = {
    1 : "😵‍💫",
    2 : "🥴",
    3 : "😶‍🌫️",
    4 : "🤯"
}


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