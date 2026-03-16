from app.store.bot.callbacks import AnswerCallback, BackCallback, CategoryCallback, FinalCategoryCallback, GameModeCallback, QuestionCallback
from app.store.tg_api.game_constants import GameModes, BotButtons, BotCommands

MENU_TEXT = (
    "🏠 Меню"
    "\n\n 🧭 Основная навигация"
    f"\n{BotCommands.start_game} – {BotButtons.start_game}"
    f"\n{BotCommands.exit_lobby} – {BotButtons.exit_lobby}"
    f"\n{BotCommands.stats} – {BotButtons.statistics}"
    f"\n{BotCommands.rules} – {BotButtons.rules}"
    
    f"\n\n 🎮 Команды в игре"
    f"\n{BotCommands.surrender} – {BotButtons.surrender}"
    f"\n{BotCommands.finish_game} – {BotButtons.finish_game}"
)

RULES_TEXT = (
    "📜 <b>ПРАВИЛА ИГРЫ «SVARME»</b>\n\n"
    "\n🕹 <b>ОБЫЧНЫЙ РЕЖИМ</b>\n\n"
    "1️⃣ <b>Раунд 1</b>\n"
    "• Случайный игрок выбирает тему и стоимость.\n"
    "• Нужно успеть нажать на кнопку быстрее соперников.\n"
    "• ✅ Верный ответ: <code>+очки</code>\n"
    "• ❌ Ошибка: <code>-очки</code>\n\n"
    "2️⃣ <b>Раунды 2 и 3</b>\n"
    "• Правила те же, но право первого хода у игрока с <i>наименьшим</i> счётом.\n\n"
    "🏁 <b>Финальный раунд</b>\n"
    "• Допускаются только игроки с <b>положительным</b> счётом.\n"
    "• Игроки по очереди удаляют темы, пока не останется одна.\n"
    "• Делаются скрытые ставки. Кто набрал больше всех по итогу — <b>Победитель</b>! 🏆\n\n"
    "\n⚡️ <b>БЫСТРАЯ ИГРА</b>\n\n"
    "• Сокращенный формат: 3 категории по 3 вопроса.\n"
    "• Всего 2 этапа: <u>Обычный раунд</u> и <u>Финал</u>.\n\n"
    "<i>🍀 Удачи в сражении умов!</i>"
)

GAME_START_TEXT = "🎉 Игра началась!"\
    f"\n{BotCommands.rules} – 📜 Правила"\
    f"\n{BotCommands.surrender} – 🏳️ Сдаться"

MENU_BUTTONS = [
    [{"text": BotButtons.start_game}, {"text": BotButtons.statistics}],
    [{"text": BotButtons.rules}, {"text": BotButtons.menu}],
]

IN_LOBBY_BUTTONS = [
    [{"text": BotButtons.exit_lobby}, {"text": BotButtons.statistics}],
    [{"text": BotButtons.rules}, {"text": BotButtons.menu}],
]

GAME_BUTTONS = [[ {"text": BotButtons.finish_game}, {"text": BotButtons.surrender}],
                [{"text": BotButtons.rules}]]


def build_answer_button() -> dict:
    return {"inline_keyboard": [[{"text": "✋ Ответить!", "callback_data": AnswerCallback.prefix}]]}


def build_game_mode_keyboard() -> dict:
    row = [
        {"text": mode.labels, "callback_data": GameModeCallback.create_data(game_mode=mode.value)}
        for mode in GameModes
    ]
    return {"inline_keyboard": [row]}


def build_category_board(categories) -> dict:
    """Category selection screen: category name buttons, 2 per row."""
    rows = []
    for i in range(0, len(categories), 2):
        row = [
            {"text": cat.name, "callback_data": CategoryCallback.create_data(category_id=cat.id)}
            for cat in categories[i : i + 2]
        ]
        rows.append(row)
    return {"inline_keyboard": rows}


def build_final_category_remove_keyboard(categories) -> dict:
    """Final round: category removal screen, 2 per row. callback_data: 'fcat:{cat.id}'"""
    rows = []
    for i in range(0, len(categories), 2):
        row = [
            {"text": cat.name, "callback_data": FinalCategoryCallback.create_data(category_id=cat.id)}
            for cat in categories[i : i + 2]
        ]
        rows.append(row)
    return {"inline_keyboard": rows}


def build_question_keyboard(questions) -> dict:
    """Price selection screen for one category.

    Price buttons sorted ascending (3 per row) + Back button.
    callback_data: "q:{question_id}"
    """
    rows = []
    row = []
    for q in sorted(questions, key=lambda q: q.price):
        row.append({"text": str(q.price), "callback_data": QuestionCallback.create_data(question_id=q.id)})
        if len(row) == 3:
            rows.append(row)
            row = []
    if row:
        rows.append(row)
    rows.append([{"text": "← Назад", "callback_data": BackCallback.prefix}])
    return {"inline_keyboard": rows}
