from app.store.tg_api.accessor import (
    BotButtons,
    BotCommands,
    CATEGORIES,
    build_category_keyboard,
    build_question_keyboard,
)


class BotManager:
    def __init__(self, app):
        self.app = app

    async def handle_update(self, update: dict):
        if "message" in update:
            message = update["message"]
            chat_id = message["chat"]["id"]
            text = message.get("text", "")

            if text == "/start":
                await self.app.store.tg_api.send_message(
                    chat_id,
                    "👋 Добро пожаловать в Svarme!"
                    '\n Svarme – игра-викторина по мотивам "Своей игры"',
                )
                await self.app.store.tg_api.send_start_menu(chat_id)
            elif text in (BotButtons.start_game, BotCommands.start_game):
                await self.app.store.tg_api.send_game_mode_choose_keyboard(chat_id)
                # await self.app.store.tg_api.send_game_menu(chat_id)
                # await self.app.store.tg_api.send_category_keyboard(chat_id)
            elif text in (BotButtons.statistics, BotCommands.stats):
                await self.app.store.tg_api.send_message(
                    chat_id, "У вас нет ни одной игры. Невозможно собрать статистику"
                )
            elif text in (BotButtons.rules, BotCommands.rules):
                await self.app.store.tg_api.send_message(
                    chat_id,
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
                    "• Сокращенный формат: 3 категории по 4 вопроса.\n"
                    "• Всего 2 этапа: <u>Обычный раунд</u> и <u>Финал</u>.\n\n"
                    "<i>🍀 Удачи в сражении умов!</i>",
                )
            elif text in (BotButtons.menu, BotCommands.menu):
                await self.app.store.tg_api.send_start_menu(chat_id)
            elif text in (BotButtons.surrender):
                await self.app.store.tg_api.send_message(chat_id, "Вы сдались! 😢")
                await self.app.store.tg_api.send_start_menu(chat_id)
            elif text:
                await self.app.store.tg_api.send_message(chat_id, text)

        elif "callback_query" in update:
            callback = update["callback_query"]
            chat_id = callback["message"]["chat"]["id"]
            message_id = callback["message"]["message_id"]
            data = callback["data"]

            await self.app.store.tg_api.answer_callback(callback["id"])

            if data.startswith("cat:"):
                cat_id = int(data.split(":")[1])
                cat = next(c for c in CATEGORIES if c["id"] == cat_id)
                await self.app.store.tg_api.edit_message(
                    chat_id,
                    message_id,
                    f"📂 Категория: <b>{cat['name']}</b>\n\nВыберите стоимость вопроса:",
                    build_question_keyboard(cat_id),
                )
            elif data.startswith("q:"):
                _, cat_id_str, price = data.split(":")
                cat = next(c for c in CATEGORIES if c["id"] == int(cat_id_str))
                await self.app.store.tg_api.delete_message(chat_id, message_id)
                await self.app.store.tg_api.send_message(
                    chat_id,
                    f"❓ Вопрос за <b>{price}</b> очков из категории <b>{cat['name']}</b>",
                )
            elif data.startswith("gm:"):
                _, game_mode = data.split(":")
                await self.app.store.tg_api.delete_message(chat_id, message_id)
                
                if game_mode == "standart":
                    await self.app.store.tg_api.send_game_menu(chat_id)
                    await self.app.store.tg_api.send_category_keyboard(chat_id)
                elif game_mode == "blitz":
                    await self.app.store.tg_api.send_game_menu(chat_id)
                    await self.app.store.tg_api.send_category_keyboard(chat_id)
            elif data == "back":
                await self.app.store.tg_api.edit_message(
                    chat_id,
                    message_id,
                    "📋 Выберите категорию:",
                    build_category_keyboard(),
                )
