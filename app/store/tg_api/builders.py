from app.store.tg_api.game_constants import CATEGORIES, QUESTION_PRICES, GameModes, BotButtons, BotCommands

MENU_TEXT = "🏠 Меню" \
            "\n\n 🗺 Основная навигация"\
            f"\n{BotCommands.start_game} – 🚀 Начать игру"\
            f"\n{BotCommands.stats} – 🏆 Статистика"\
            f"\n{BotCommands.rules} – 📜 Правила"

RULES_TEXT = "📜 <b>ПРАВИЛА ИГРЫ «SVARME»</b>\n\n"\
                    "\n🕹 <b>ОБЫЧНЫЙ РЕЖИМ</b>\n\n"\
                    "1️⃣ <b>Раунд 1</b>\n"\
                    "• Случайный игрок выбирает тему и стоимость.\n"\
                    "• Нужно успеть нажать на кнопку быстрее соперников.\n"\
                    "• ✅ Верный ответ: <code>+очки</code>\n"\
                    "• ❌ Ошибка: <code>-очки</code>\n\n"\
                    "2️⃣ <b>Раунды 2 и 3</b>\n"\
                    "• Правила те же, но право первого хода у игрока с <i>наименьшим</i> счётом.\n\n"\
                    "🏁 <b>Финальный раунд</b>\n"\
                    "• Допускаются только игроки с <b>положительным</b> счётом.\n"\
                    "• Игроки по очереди удаляют темы, пока не останется одна.\n"\
                    "• Делаются скрытые ставки. Кто набрал больше всех по итогу — <b>Победитель</b>! 🏆\n\n"\
                    "\n⚡️ <b>БЫСТРАЯ ИГРА</b>\n\n"\
                    "• Сокращенный формат: 3 категории по 4 вопроса.\n"\
                    "• Всего 2 этапа: <u>Обычный раунд</u> и <u>Финал</u>.\n\n"\
                    "<i>🍀 Удачи в сражении умов!</i>"

GAME_START_TEXT = "Игра началась!"

SURRENDER_TEXT = "Вы сдались! 😢"

MENU_BUTTONS = [
                [{"text": BotButtons.start_game}, {"text": BotButtons.statistics}],
                [{"text": BotButtons.rules}, {"text" : BotButtons.menu}]
            ]

GAME_BUTTONS = [[{"text": BotButtons.rules}, {"text" : BotButtons.surrender}]]


def build_game_mode_keyboard() -> dict:
    row = []
    for mode in GameModes:
        row.append({
            "text": mode.labels, "callback_data": f"gm:{mode.value}"
        })
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