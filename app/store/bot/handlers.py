from app.store.bot.router import BotRouter
from app.store.tg_api.builers import GAME_BUTTONS, GAME_START_TEXT, MENU_BUTTONS, MENU_TEXT, RULES_TEXT, SURRENDER_TEXT, build_category_keyboard, build_question_keyboard
from app.store.tg_api.game_constants import CATEGORIES, BotButtons, BotCommands, GameModes

router = BotRouter()

@router.message("/start")
async def handle_start(self, chat_id: int):
    await self.app.store.tg_api.send_message(chat_id, "👋 Добро пожаловать в Svarme!")
    await self.app.store.tg_api.send_keyboard(chat_id, MENU_BUTTONS, MENU_TEXT)

@router.message(BotCommands.start_game, BotButtons.start_game)
async def handle_start_game(self, chat_id: int):
    await self.app.store.tg_api.send_game_mode_choose_keyboard(chat_id)

@router.callback("cat:")
async def handle_category_click(self, chat_id, message_id, data):
    cat_id = int(data.split(":")[1])
    cat = next(c for c in CATEGORIES if c["id"] == cat_id)
    await self.app.store.tg_api.edit_message(
        chat_id, message_id,
        f"📂 Категория: <b>{cat['name']}</b>\n\nВыберите стоимость:",
        build_question_keyboard(cat_id)
    )

@router.message(BotCommands.stats, BotButtons.statistics)
async def handle_stats(self, chat_id: int):
    await self.app.store.tg_api.send_message(chat_id, "У вас нет ни одной игры. Невозможно собрать статистику")

@router.message(BotCommands.rules, BotButtons.rules)
async def handle_rules(self, chat_id: int):
    await self.app.store.tg_api.send_message(chat_id, RULES_TEXT)

@router.message(BotCommands.menu, BotButtons.menu)
async def handle_menu(self, chat_id: int):
    await self.app.store.tg_api.send_keyboard(chat_id, MENU_BUTTONS, MENU_TEXT)

@router.message(BotCommands.surrender, BotButtons.surrender)
async def handle_surrender(self, chat_id: int):
    await self.app.store.tg_api.send_message(chat_id, SURRENDER_TEXT)
    await self.app.store.tg_api.send_keyboard(chat_id, MENU_BUTTONS, MENU_TEXT)

@router.callback("q:")
async def handle_question_click(self, chat_id, message_id, data):
    _, cat_id_str, price = data.split(":")
    cat = next(c for c in CATEGORIES if c["id"] == int(cat_id_str))
    await self.app.store.tg_api.delete_message(chat_id, message_id)
    await self.app.store.tg_api.send_message(
        chat_id,
        f"Вы выбрали вопрос из категории <b>{cat['name']}</b> стоимостью <b>{price}</b> очков.\n\n(Здесь будет текст вопроса и варианты ответов)",
    )

@router.callback("gm:")
async def handle_game_mode_click(self, chat_id, message_id, data):
    _, game_mode = data.split(":")
    await self.app.store.tg_api.delete_message(chat_id, message_id)
    await self.app.store.tg_api.send_keyboard(chat_id, GAME_BUTTONS, GAME_START_TEXT)
    if game_mode == GameModes.STANDART.value:
        await self.app.store.tg_api.send_category_keyboard(chat_id)
    elif game_mode == GameModes.BLITZ.value:
        await self.app.store.tg_api.send_category_keyboard(chat_id)

@router.callback("back")
async def handle_back_click(self, chat_id, message_id): 
    await self.app.store.tg_api.edit_message(
                chat_id,
                message_id,
                "📋 Выберите категорию:",
                build_category_keyboard(),
            )