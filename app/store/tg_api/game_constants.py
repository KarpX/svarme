from enum import Enum

class BotButtons:
    start_game = "🚀 Начать игру"
    statistics = "🏆 Статистика"
    rules = "📜 Правила"
    menu = "☰ Меню"

    surrender = "🏳️ Сдаться"
    finish_game = "🏁 Закончить игру"

    exit_lobby = "⛓️‍💥 Выйти из лобби"


class BotCommands:
    start_game = "/game"
    rules = "/rules"
    stats = "/stats"
    menu = "/menu"

    surrender = "/surr"
    finish_game = "/finish"

    exit_lobby = "/leave"

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
    
    @property
    def questions(self):
        questions = {
            GameModes.STANDART : 5,
            GameModes.BLITZ : 3
        }

        return questions[self]
    
    @property
    def categories(self):
        categories = {
            GameModes.STANDART : 5,
            GameModes.BLITZ : 3
        }

        return categories[self]
    
class ChatType(Enum):
    PRIVATE = "private"
    GROUP = "group"

class GameStatus(Enum):
    WAITING = "waiting"
    PENDING = "pending"
    FINAL_BETTING = "final_betting"
    FINAL_ANSWERING = "final_answering"
    FINAL_REMOVING = "final_removing"
    ANSWERING = "answering"
    CHOOSING_QUESTION = "choosing_question"
    FINISHED = "finished"

class GameTimers(Enum):
    CHOOSE_TIMEOUT = 30   # секунд на выбор категории/вопроса
    ANSWER_TIMEOUT = 15   # секунд на нажатие кнопки "ответить"
    ANSWERING_TIMEOUT = 15  # секунд на ввод ответа
