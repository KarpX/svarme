import random

from app.store.bot.callbacks import AnswerCallback, BackCallback, CategoryCallback, GameModeCallback, QuestionCallback, StartGameCallback
from app.store.bot.router import BotRouter
from app.store.tg_api.builders import (
    GAME_BUTTONS,
    GAME_START_TEXT,
    MENU_BUTTONS,
    MENU_TEXT,
    RULES_TEXT,
    build_answer_button,
    build_category_board,
    build_game_mode_keyboard,
    build_question_keyboard,
)
from app.store.tg_api.game_constants import BotButtons, BotCommands

router = BotRouter()


@router.message("/start")
async def handle_start(self, chat_id: int, user_id: int):
    await self.app.store.tg_api.send_message(chat_id, "👋 Добро пожаловать в Svarme!")
    await self.app.store.tg_api.send_keyboard(chat_id, MENU_BUTTONS, MENU_TEXT)


@router.message(BotCommands.start_game, BotButtons.start_game, BotCommands.start_game + "@SvarMeBot")
async def handle_start_game(self, chat_id: int, user_id: int):
    # Check if game already running in this chat
    active = await self.app.store.game.get_active_game(chat_id)
    if active:
        await self.app.store.tg_api.send_message(chat_id, "⚠️ Игра уже идёт в этом чате!")
        return

    waiting = self.app["waiting"]
    if chat_id not in waiting:
        waiting[chat_id] = set()
    waiting[chat_id].add(user_id)

    if len(waiting[chat_id]) < 2:
        await self.app.store.tg_api.send_message(
            chat_id,
            f"✅ Вы записались в игру! Ожидаем ещё игроков... ({len(waiting[chat_id])}/4)",
        )
        return
    
    elif len(waiting[chat_id]) > 4:
        waiting[chat_id].remove(user_id)
        await self.app.store.tg_api.send_message(chat_id, "❌ Максимальное количество игроков — 4. Вы не были добавлены в игру.")
        return
    
    elif len(waiting[chat_id]) >= 2:
        await self.app.store.tg_api.send_inline_keyboard(
            chat_id,
            f"✅ Достаточно игроков! {len(waiting[chat_id])}/4. Нажмите кнопку ниже, чтобы начать игру.",
            {"inline_keyboard": [[{"text": "🚀 Начать игру!", "callback_data": "start_game"}]]},
        )


@router.message(BotCommands.stats, BotButtons.statistics, BotCommands.stats + "@SvarMeBot")
async def handle_stats(self, chat_id: int, user_id: int):
    user = await self.app.store.user.get_user(user_id)
    if not user:
        await self.app.store.tg_api.send_message(
            chat_id, "У вас нет ни одной игры. Невозможно собрать статистику"
        )
        return
    user_name = user.display_name if user else f"ID:{user_id}"
    stats = await self.app.store.game.get_user_statistics(user_id)
    await self.app.store.tg_api.send_message(
        chat_id,
        f"📊 <b>Статистика</b> {user_name}:\n\n"
        f"🎮 Всего игр: {stats.games_played}\n"
        f"🏆 Побед: {stats.wins}\n"
        f"🚀 Лучший результат: {stats.max_points} очков\n"
        f"✅Всего правильных ответов: {stats.right_answers}",
    )

@router.message(BotCommands.rules, BotButtons.rules, BotCommands.rules + "@SvarMeBot")
async def handle_rules(self, chat_id: int, user_id: int):
    await self.app.store.tg_api.send_message(chat_id, RULES_TEXT)


@router.message(BotCommands.menu, BotButtons.menu, BotCommands.menu + "@SvarMeBot")
async def handle_menu(self, chat_id: int, user_id: int):
    await self.app.store.tg_api.send_keyboard(chat_id, MENU_BUTTONS, MENU_TEXT)


async def _finish_game(self, chat_id: int, game_id: int):
    """Mark game finished, announce results, update statistics."""
    players = await self.app.store.game.get_players(game_id)
    await self.app.store.game.update_game(game_id, status="finished")

    if not players:
        await self.app.store.tg_api.send_message(chat_id, "🏁 Игра завершена. Участников не осталось.")
        await self.app.store.tg_api.send_keyboard(chat_id, MENU_BUTTONS, MENU_TEXT)
        return

    sorted_players = sorted(players, key=lambda p: p.points, reverse=True)
    winner = sorted_players[0]
    winner_user = await self.app.store.user.get_user(winner.id)
    winner_name = winner_user.display_name if winner_user else f"ID:{winner.id}"

    lines = ["🏁 <b>Игра завершена!</b>\n\n📊 Итоговые результаты:"]
    for i, p in enumerate(sorted_players, start=1):
        p_user = await self.app.store.user.get_user(p.id)
        p_name = p_user.display_name if p_user else f"ID:{p.id}"
        medal = {1: "🥇", 2: "🥈", 3: "🥉"}.get(i, f"{i}.")
        lines.append(f"{medal} {p_name} — <b>{p.points}</b> очков")
    lines.append(f"\n🏆 Победитель: <b>{winner_name}</b> с {winner.points} очками!")

    await self.app.store.tg_api.send_message(chat_id, "\n".join(lines))
    await self.app.store.tg_api.send_keyboard(chat_id, MENU_BUTTONS, MENU_TEXT)

    right_answers = self.app["right_answers"].pop(chat_id, {})
    await self.app.store.game.update_statistics(players, winner.id, right_answers)


@router.message(BotCommands.surrender, BotButtons.surrender, BotCommands.surrender + "@SvarMeBot")
async def handle_surrender(self, chat_id: int, user_id: int):
    game = await self.app.store.game.get_active_game(chat_id)
    if not game:
        await self.app.store.tg_api.send_message(chat_id, "❌ Нет активной игры, в которой можно сдаться.")
        return

    # Remove the surrendering player from the game
    await self.app.store.game.remove_player(user_id)
    await self.app.store.tg_api.send_message(chat_id, f"🏳 Игрок ID:{user_id} сдался!")

    remaining = await self.app.store.game.get_players(game.id)
    if len(remaining) <= 1:
        await _finish_game(self, chat_id, game.id)
    else:
        # If the surrendering player was the chooser, pass turn to someone else
        if game.choosing_user_id == user_id:
            new_chooser = remaining[0].id
            await self.app.store.game.update_game(game.id, choosing_user_id=new_chooser, status="choosing_question")
            await _announce_chooser(self, chat_id, new_chooser)
            await _send_category_board(self, chat_id)


async def _send_category_board(self, chat_id: int, message_id: int | None = None):
    """Load 5 random round-1 categories and show the category selection board."""
    game = await self.app.store.game.get_active_game(chat_id)
    answered_ids = await self.app.store.game.get_answered_question_ids(game.id) if game else set()

    categories = await self.app.store.quiz.get_random_categories_for_round(round=1)
    # Filter out categories where all questions are already answered
    categories = [c for c in categories if any(q.id not in answered_ids for q in c.questions)]

    if not categories:
        text = "❌ В базе нет категорий для этого раунда. Обратитесь к администратору."
        await self.app.store.tg_api.send_message(chat_id, text)
        return

    text = "📋 Выберите категорию:"
    keyboard = build_category_board(categories)
    if message_id is not None:
        await self.app.store.tg_api.edit_message(chat_id, message_id, text, keyboard)
    else:
        await self.app.store.tg_api.send_inline_keyboard(chat_id, text, keyboard)


async def _announce_chooser(self, chat_id: int, choosing_user_id: int):
    user = await self.app.store.user.get_user(choosing_user_id)
    name = user.display_name if user else f"ID:{choosing_user_id}"
    await self.app.store.tg_api.send_message(
        chat_id,
        f"🎯 Ход игрока <b>{name}</b>. Выберите категорию и вопрос:",
    )


@router.callback(GameModeCallback)
async def handle_game_mode_click(self, chat_id, message_id, data, user_id: int):
    await self.app.store.tg_api.delete_message(chat_id, message_id)

    player_ids = self.app["pending_players"].pop(chat_id, None)

    if not player_ids:
        await self.app.store.tg_api.send_message(chat_id, "❌ Не удалось найти игроков.")
        return

    # Create game in DB
    game = await self.app.store.game.create_game(
        chat_id=chat_id,
        game_mode=data.game_mode,
        game_type="group",
    )

    # Register all players
    for uid in player_ids:
        await self.app.store.user.get_or_create_user(uid)
        await self.app.store.game.add_player(uid, game.id)

    # Pick random first chooser
    choosing_user_id = random.choice(player_ids)
    await self.app.store.game.update_game(game.id, choosing_user_id=choosing_user_id)

    await self.app.store.tg_api.send_keyboard(chat_id, GAME_BUTTONS, GAME_START_TEXT)
    await _announce_chooser(self, chat_id, choosing_user_id)
    await _send_category_board(self, chat_id)


@router.callback(CategoryCallback)
async def handle_category_click(self, chat_id, message_id, data, user_id: int):
    game = await self.app.store.game.get_active_game(chat_id)
    if not game or game.status != "choosing_question":
        return
    if game.choosing_user_id != user_id:
        return

    answered_ids = await self.app.store.game.get_answered_question_ids(game.id)
    questions = await self.app.store.quiz.list_questions(category_id=data.category_id, exclude_ids=answered_ids)
    category = await self.app.store.quiz.get_category_by_id(data.category_id)
    if not questions or not category:
        return

    await self.app.store.tg_api.edit_message(
        chat_id,
        message_id,
        f"📂 Категория: <b>{category.name}</b>\n\nВыберите стоимость:",
        build_question_keyboard(questions),
    )


@router.callback(QuestionCallback)
async def handle_question_click(self, chat_id, message_id, data, user_id: int):
    game = await self.app.store.game.get_active_game(chat_id)
    if not game or game.status != "choosing_question":
        return
    if game.choosing_user_id != user_id:
        return

    question = await self.app.store.quiz.get_question_by_id(data.question_id)
    if not question:
        return

    await self.app.store.game.update_game(
        game.id,
        active_question_id=question.id,
        status="answering",
        choosing_user_id=None,
    )

    await self.app.store.tg_api.delete_message(chat_id, message_id)
    await self.app.store.tg_api.send_message(
        chat_id,
        f"📂 Категория: <b>{question.category.name}</b>\n"
        f"💰 Стоимость: <b>{question.price}</b>\n\n"
        f"❓ {question.text}",
    )
    await self.app.store.tg_api.send_inline_keyboard(
        chat_id, "⚡ Кто первый знает ответ?", build_answer_button()
    )


@router.callback(AnswerCallback)
async def handle_answer_button_click(self, chat_id, message_id, data, user_id: int):
    user = await self.app.store.user.get_user(user_id)
    name= user.display_name if user else f"ID:{user_id}"
    game = await self.app.store.game.get_active_game(chat_id)
    if not game or game.status != "answering":
        return
    if game.choosing_user_id is not None:
        # Someone already claimed the answer slot
        return

    # Lock the answerer
    await self.app.store.game.update_game(game.id, choosing_user_id=user_id)

    # Remove the answer button
    await self.app.store.tg_api.edit_message(
        chat_id, message_id, "⚡ Кто первый знает ответ?", {"inline_keyboard": []}
    )
    await self.app.store.tg_api.send_message(
        chat_id, f"✋ Отвечает <b>{name}</b>! Напишите ваш ответ:"
    )


@router.callback(BackCallback)
async def handle_back_click(self, chat_id, message_id, data, user_id: int):
    game = await self.app.store.game.get_active_game(chat_id)
    if game and game.choosing_user_id != user_id:
        return
    await _send_category_board(self, chat_id, message_id=message_id)

@router.callback(StartGameCallback)
async def handle_start_game_click(self, chat_id, message_id, data, user_id: int):
    waiting = self.app.get("waiting", {})
    if chat_id not in waiting or user_id not in waiting[chat_id]:
        await self.app.store.tg_api.send_message(chat_id, "❌ Вы не были в списке игроков.")
        return

    # Enough players — start the game
    player_ids = list(waiting.pop(chat_id))
    await self.app.store.tg_api.send_inline_keyboard(
        chat_id, "🎮 Выберите режим игры", build_game_mode_keyboard()
    )
    self.app["pending_players"][chat_id] = player_ids


async def handle_answer_message(self, chat_id: int, user_id: int, text: str):
    """Called from BotManager when game is in 'answering' state and user_id == choosing_user_id."""
    game = await self.app.store.game.get_active_game(chat_id)
    if not game or not game.active_question_id:
        return

    question = await self.app.store.quiz.get_question_by_id(game.active_question_id)
    if not question:
        return
    
    answer_list = question.answer.split(":")
    user = await self.app.store.user.get_user(user_id)
    user_name = user.display_name if user else f"ID:{user_id}"

    if text.strip().lower() == answer_list[0].strip().lower(): # Пока пусть только первый вариант будет. Потом думаем что можно
        # Correct answer
        right_answers = self.app["right_answers"].setdefault(chat_id, {})
        right_answers[user_id] = right_answers.get(user_id, 0) + 1

        await self.app.store.game.add_answered_question(game.id, question.id)
        new_points = await self.app.store.game.update_player_points(user_id, question.price)
        await self.app.store.tg_api.send_message(
            chat_id,
            f"✅ Верно! Ответ: <b>{question.answer}</b>\n"
            f"💰 +{question.price} очков. Счёт игрока {user_name}: <b>{new_points}</b>",
        )
        # Winner gets to choose next question
        await self.app.store.game.update_game(
            game.id,
            status="choosing_question",
            choosing_user_id=user_id,
            active_question_id=None,
        )
        await _announce_chooser(self, chat_id, user_id)
        await _send_category_board(self, chat_id)
    else:
        # Wrong answer
        new_points = await self.app.store.game.update_player_points(user_id, -question.price)
        await self.app.store.tg_api.send_message(
            chat_id,
            f"❌ Неверно! Ответ игрока {user_name}: «{text}»\n"
            f"💸 -{question.price} очков. Счёт: <b>{new_points}</b>\n\n"
            f"Кто ещё знает ответ?",
        )
        # Release the lock — button becomes active again
        await self.app.store.game.update_game(game.id, choosing_user_id=None)
        await self.app.store.tg_api.send_inline_keyboard(
            chat_id, "⚡ Кто первый знает ответ?", build_answer_button()
        )
