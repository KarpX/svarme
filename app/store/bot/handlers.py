import asyncio
import random

from app.store.bot.callbacks import AnswerCallback, BackCallback, CategoryCallback, ExitLobbyCallback, FinalCategoryCallback, FinishGameCallback, FinishGameVoteCallback, GameModeCallback, JoinLobbyCallback, QuestionCallback, StartGameCallback
from app.store.bot.router import BotRouter
from app.store.tg_api.builders import (
    GAME_BUTTONS,
    GAME_START_TEXT,
    IN_LOBBY_BUTTONS,
    MENU_BUTTONS,
    MENU_TEXT,
    RULES_TEXT,
    build_answer_button,
    build_category_board,
    build_final_category_remove_keyboard,
    build_game_mode_keyboard,
    build_question_keyboard,
)
from app.store.tg_api.game_constants import SURR_FACES, BotButtons, BotCommands, GameModes, GameStatus
from app.web import logger
from app.web.utils import ratelimit

router = BotRouter()

@router.message("/start")
@ratelimit(seconds=15)
async def handle_start(self, chat_id: int, user_id: int):
    await self.app.store.tg_api.send_message(chat_id, "👋 Добро пожаловать в Svarme!")
    await self.app.store.tg_api.send_keyboard(chat_id, MENU_BUTTONS, MENU_TEXT)

async def _send_lobby(self, chat_id: int, user_id: int, message_id: int = None):
    game = await self.app.store.game.get_lobby_game(chat_id)

    if not game:
        if message_id:
            await self.app.store.tg_api.delete_message(chat_id, message_id)
        return

    lobby_players = await self.app.store.game.get_lobby_players(chat_id)
    
    player_names = []
    for p in lobby_players:
        username = p.display_name if p else f'ID:{p}'
        player_names += [f"\n🟢 {username} 👑" if p.id == game.choosing_user_id else f"\n🟢 {username}"]
    empty_players = "\n⚪ Пусто"*(4 - len(lobby_players))
    text = f"🎮 <b>Лобби игры</b>\n\nИгроки:"\
    f"{''.join(player_names)}{empty_players} \n\nВсего: {len(lobby_players)}/4"

    logger.logging.info(game.choosing_user_id)

    is_in_lobby = any(p.id == user_id for p in lobby_players)

    buttons = []
    if not is_in_lobby and len(lobby_players) < 4:
        buttons.append([{"text" : "❤️‍🔥 Присоединиться к игре", "callback_data" : JoinLobbyCallback.prefix}])
    elif is_in_lobby:
        buttons.append([{"text" : "💔 Покинуть лобби", "callback_data" : ExitLobbyCallback.prefix}])
    
    if len(lobby_players) >= 2:
        buttons.append([{"text" : "🚀 Начать игру!", "callback_data": StartGameCallback.prefix}])

    keyboard = {"inline_keyboard": buttons}

    if message_id:
        await self.app.store.tg_api.edit_message(chat_id, message_id, text, keyboard)

    else:
        await self.app.store.tg_api.send_inline_keyboard(
            chat_id,
            text,
            keyboard,
        )


@router.message(BotCommands.start_game, BotButtons.start_game, BotCommands.start_game + "@SvarMeBot")
@ratelimit(seconds=5)
async def handle_start_game(self, chat_id: int, user_id: int, message_id = None):
    # Check if game already running in this chat
    active = await self.app.store.game.get_active_game(chat_id)
    if active:
        await self.app.store.tg_api.send_message(chat_id, "⚠️ Игра уже идёт в этом чате!")
        return

    user = await self.app.store.user.get_or_create_user(user_id)
    user_name = user.display_name if user else f"ID:{user_id}"

    lobby_players = await self.app.store.game.get_lobby_players(chat_id)
    if any(p.id == user_id for p in lobby_players):
        await self.app.store.tg_api.send_message(chat_id, f"⛔ {user_name} уже в лобби!")
        return
    
    if len(lobby_players) >= 4:
        await self.app.store.tg_api.send_message(chat_id, f"❌ Максимальное количество игроков — 4. {user_name} не был добавлен в игру.")
        return
    
    await self.app.store.game.add_lobby_player(chat_id, user_id)
    lobby_players = await self.app.store.game.get_lobby_players(chat_id)

    await self.app.store.tg_api.send_message(chat_id, f"✅ {user_name} записался в игру! Ожидаем ещё игроков... ({len(lobby_players)}/4)")

    await _send_lobby(self, chat_id, user_id, message_id)
    
    

@router.message(BotCommands.exit_lobby, BotCommands.exit_lobby + "@SvarMeBot")
@ratelimit(seconds=5)
async def handle_exit_lobby(self, chat_id: int, user_id: int, message_id = None):
    players = await self.app.store.game.get_lobby_players(chat_id)
    user = await self.app.store.user.get_user(user_id)
    user_name = user.display_name if user else f"ID:{user_id}"

    if not any(p.id == user_id for p in players):
        await self.app.store.tg_api.send_message(chat_id, f"❌ {user_name} не в лобби")
        return
    
    await self.app.store.game.remove_lobby_player(chat_id, user_id)

    await self.app.store.tg_api.send_keyboard(chat_id, MENU_BUTTONS, f"💨 {user_name} вышел из лобби!")

    await _send_lobby(self, chat_id, user_id, message_id)

@router.message(BotCommands.stats, BotButtons.statistics, BotCommands.stats + "@SvarMeBot")
@ratelimit(seconds=10)
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
@ratelimit(seconds=10)
async def handle_rules(self, chat_id: int, user_id: int):
    await self.app.store.tg_api.send_message(chat_id, RULES_TEXT)

@router.message(BotCommands.menu, BotButtons.menu, BotCommands.menu + "@SvarMeBot")
@ratelimit(seconds=2)
async def handle_menu(self, chat_id: int, user_id: int):
    await self.app.store.tg_api.send_keyboard(chat_id, MENU_BUTTONS, MENU_TEXT)

@router.message(BotCommands.finish_game, BotButtons.finish_game, BotCommands.finish_game + "@SvarMeBot")
@ratelimit(seconds=10)
async def handle_finish_game(self, chat_id: int, user_id: int):
    game = await self.app.store.game.get_active_game(chat_id)
    if not game:
        await self.app.store.tg_api.send_message(chat_id, "❌ Нет активной игры.")
        return

    if not await self.app.store.game.is_player(game.id, user_id):
        return

    game_id = game.id
    user = await self.app.store.user.get_user(user_id)
    user_name = user.display_name if user else f"ID:{user_id}"

    if await self.app.store.game.has_finish_vote(game_id, user_id):
        await self.app.store.tg_api.send_message(chat_id, f"⚠️ {user_name} уже проголосовал за завершение.")
        return

    await self.app.store.game.add_finish_vote(game_id, user_id)

    need_to_finish = max(len(await self.app.store.game.get_players(game_id)) // 2, 2)
    current_votes = await self.app.store.game.count_finish_votes(game_id)
    await self.app.store.tg_api.send_message(chat_id, f"{SURR_FACES[current_votes]} {user_name} хочет сдаться.")

    if current_votes >= need_to_finish:
        await self.app.store.tg_api.send_message(chat_id, "‼️ <b>Голосование завершено!</b> Большинство за остановку игры.")
        await self.app.store.game.clear_finish_votes(game_id)

        players = await self.app.store.game.get_players(game_id)
        eligible = [p for p in players if p.points > 0]

        if len(eligible) < 1:
            await self.app.store.tg_api.send_message(chat_id, "💔 Нет ни одного игрока с положительным счётом.")

        for p in players:
            if p.points <= 0:
                await self.app.store.game.remove_player(p.id)

        await _finish_game(self, chat_id, game_id)
    else:
        filled = "🟢" * current_votes
        empty = "⚪" * (need_to_finish - current_votes)
        
        text = (
            f"🏳 <b>Голосование за досрочное завершение</b>\n\n"
            f"Игрок <b>{user_name}</b> предложил закончить игру.\n"
            f"Статус: {filled}{empty} ({current_votes}/{need_to_finish})\n\n"
            f"<i>Чтобы поддержать, нажмите кнопку ниже или введите команду еще раз.</i>"
        )
        
        keyboard = {
            "inline_keyboard": [[
                {"text": "🏳 Поддержать завершение", "callback_data": FinishGameVoteCallback.prefix}
            ]]
        }
        await self.app.store.tg_api.send_inline_keyboard(chat_id, text, keyboard)


async def _finish_game(self, chat_id: int, game_id: int):
    """Mark game finished, announce results, update statistics."""
    players = await self.app.store.game.get_players(game_id)
    await self.app.store.game.update_game(game_id, status=GameStatus.FINISHED.value)

    if not players:
        await self.app.store.tg_api.send_message(chat_id, "🏁 Игра завершена. Участников не осталось.")
        await self.app.store.tg_api.send_keyboard(chat_id, MENU_BUTTONS, MENU_TEXT)
        return

    sorted_players = sorted(players, key=lambda p: p.points, reverse=True)
    winner = sorted_players[0]
    winner_user = await self.app.store.user.get_user(winner.id)
    winner_name = winner_user.display_name if winner_user else f"ID:{winner.id}"

    await self.app.store.game.update_statistics(players, winner.id)

    lines = ["🏁 <b>Игра завершена!</b>\n\n📊 Итоговые результаты:"]
    for i, p in enumerate(sorted_players, start=1):
        p_user = await self.app.store.user.get_user(p.id)
        p_name = p_user.display_name if p_user else f"ID:{p.id}"
        medal = {1: "🥇", 2: "🥈", 3: "🥉"}.get(i, f"{i}.")
        lines.append(f"{medal} {p_name} — <b>{p.points}</b> очков")
    lines.append(f"\n🏆 Победитель: <b>{winner_name}</b> с {winner.points} очками!")

    await self.app.store.tg_api.send_message(chat_id, "\n".join(lines))
    await self.app.store.tg_api.send_keyboard(chat_id, MENU_BUTTONS, MENU_TEXT)


@router.message(BotCommands.surrender, BotButtons.surrender, BotCommands.surrender + "@SvarMeBot")
@ratelimit(seconds=60)
async def handle_surrender(self, chat_id: int, user_id: int):
    game = await self.app.store.game.get_active_game(chat_id)
    if not game:
        await self.app.store.tg_api.send_message(chat_id, "❌ Нет активной игры, в которой можно сдаться.")
        return

    if not await self.app.store.game.is_player(game.id, user_id):
        return

    user = await self.app.store.user.get_user(user_id)
    user_name = user.display_name if user else f"ID:{user_id}"

    # Remove the surrendering player from the game
    await self.app.store.game.remove_player(user_id)
    await self.app.store.tg_api.send_message(chat_id, f"🏳 Игрок {user_name} сдался!")

    remaining = await self.app.store.game.get_players(game.id)
    if len(remaining) <= 1:
        await _finish_game(self, chat_id, game.id)
    else:
        # If the surrendering player was the chooser, pass turn to someone else
        if game.choosing_user_id == user_id:
            new_chooser = remaining[0].id
            await self.app.store.game.update_game(game.id, choosing_user_id=new_chooser, status=GameStatus.CHOOSING_QUESTION.value)
            await _announce_chooser(self, chat_id, new_chooser)
            await _send_category_board(self, chat_id)


async def _send_category_board(self, chat_id: int, message_id: int | None = None):
    """Load 5 random round-1 categories and show the category selection board."""
    game = await self.app.store.game.get_active_game(chat_id)
    if not game:
        await self.app.store.tg_api.send_message(chat_id, "❌ Нет активной игры.")
        return
    
    answered_ids = await self.app.store.game.get_answered_question_ids(game.id) if game else set()
    current_categories = await self.app.store.game.get_game_categories(game.id)
    is_blitz = game.game_mode == GameModes.BLITZ.value

    if not current_categories:
        count = GameModes.BLITZ.categories if is_blitz else GameModes.STANDART.categories
        current_categories = await self.app.store.quiz.get_random_categories_for_round(game.current_round if not is_blitz else 0, limit=count)

        if game.game_mode == is_blitz:
            for cat in current_categories:
                cat.questions = random.sample(cat.questions, min(3, len(cat.questions)))
        await self.app.store.game.set_game_categories(game.id, [c.id for c in current_categories])
    
    categories = [c for c in current_categories if any(q.id not in answered_ids for q in c.questions)]

    if not categories:
        next_round = game.current_round + 1

        if next_round == 4 or (is_blitz and next_round == 2):
            await _start_final_round(self, chat_id, game.id)
            return

        await self.app.store.game.update_game(game.id, current_round=next_round)
        await self.app.store.game.clear_game_categories(game.id)

        players = await self.app.store.game.get_players(game.id)
        score_lines = []
        for p in players:
            p_user = await self.app.store.user.get_user(p.id)
            p_name = p_user.display_name if p_user else f"ID:{p.id}"
            score_lines.append(f"{p_name} — {p.points} очков")
        await self.app.store.tg_api.send_message(
            chat_id,
            f"🎉 <b>Раунд {next_round - 1} завершён!</b>\nПромежуточные результаты:\n" +
            "\n".join(score_lines) +
            f"\n\nПереходим к <b>раунду {next_round}!</b>",
        )
        await _announce_chooser(self, chat_id, game.choosing_user_id)

        return await _send_category_board(self, chat_id, message_id)

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
@ratelimit(seconds=30)
async def handle_game_mode_click(self, chat_id, message_id, data, user_id: int):
    lobby_players = await self.app.store.game.get_lobby_players(chat_id)
    if not lobby_players:
        await self.app.store.tg_api.send_message(chat_id, "❌ Не удалось найти игроков.")
        return

    if not any(p.id == user_id for p in lobby_players):
        return

    await self.app.store.tg_api.delete_message(chat_id, message_id)

    player_ids = [p.id for p in lobby_players]

    # Upgrade lobby game to a real game with chosen mode
    lobby = await self.app.store.game.get_lobby_game(chat_id)
    await self.app.store.game.update_game(
        lobby.id,
        game_mode=data.game_mode,
        status=GameStatus.CHOOSING_QUESTION.value,
    )
    game = lobby

    # Pick random first chooser
    choosing_user_id = random.choice(player_ids)
    await self.app.store.game.update_game(game.id, choosing_user_id=choosing_user_id)

    await self.app.store.tg_api.send_keyboard(chat_id, GAME_BUTTONS, GAME_START_TEXT)
    await _announce_chooser(self, chat_id, choosing_user_id)
    await _send_category_board(self, chat_id)


@router.callback(CategoryCallback)
@ratelimit(seconds=2)
async def handle_category_click(self, chat_id, message_id, data, user_id: int):
    game = await self.app.store.game.get_active_game(chat_id)
    if not game or game.status != GameStatus.CHOOSING_QUESTION.value:
        return
    if game.choosing_user_id != user_id:
        return

    answered_ids = await self.app.store.game.get_answered_question_ids(game.id)
    is_blitz = game.game_mode == GameModes.BLITZ.value
    questions = await self.app.store.quiz.list_questions(category_id=data.category_id, exclude_ids=answered_ids, limit=GameModes.BLITZ.questions if is_blitz else GameModes.STANDART.questions)
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
@ratelimit(seconds=5)
async def handle_question_click(self, chat_id, message_id, data, user_id: int):
    game = await self.app.store.game.get_active_game(chat_id)
    if not game or game.status != GameStatus.CHOOSING_QUESTION.value:
        return
    if game.choosing_user_id != user_id:
        return

    question = await self.app.store.quiz.get_question_by_id(data.question_id)
    if not question:
        return

    await self.app.store.game.update_game(
        game.id,
        active_question_id=question.id,
        status=GameStatus.ANSWERING.value,
        choosing_user_id=None,
    )

    await self.app.store.tg_api.delete_message(chat_id, message_id)
    await self.app.store.tg_api.send_message(
        chat_id,
        f"📂 Категория: <b>{question.category.name}</b>\n"
        f"💰 Стоимость: <b>{question.price}</b>\n\n"
        f"❓ {question.text}",
    )
    await asyncio.sleep(3)
    await self.app.store.tg_api.send_inline_keyboard(
        chat_id, "⚡ Кто первый знает ответ?", build_answer_button()
    )


@router.callback(AnswerCallback)
@ratelimit(seconds=5)
async def handle_answer_button_click(self, chat_id, message_id, data, user_id: int):
    user = await self.app.store.user.get_user(user_id)
    name = user.display_name if user else f"ID:{user_id}"
    game = await self.app.store.game.get_active_game(chat_id)
    if not game or game.status != GameStatus.ANSWERING.value:
        return
    if not await self.app.store.game.is_player(game.id, user_id):
        return
    if game.choosing_user_id is not None:
        # Someone already claimed the answer slot
        return

    # Lock the answerer
    await self.app.store.game.update_game(game.id, choosing_user_id=user_id)

    # Remove the answer button
    await self.app.store.tg_api.edit_message(
        chat_id, message_id, "⚡ Кто первый?", {"inline_keyboard": []}
    )
    await self.app.store.tg_api.send_message(
        chat_id, f"✋ Отвечает <b>{name}</b>! Напишите ваш ответ:"
    )


@router.callback(BackCallback)
@ratelimit(seconds=2)
async def handle_back_click(self, chat_id, message_id, data, user_id: int):
    game = await self.app.store.game.get_active_game(chat_id)
    if game and game.choosing_user_id != user_id:
        return
    await _send_category_board(self, chat_id, message_id=message_id)


@router.callback(StartGameCallback)
@ratelimit(seconds=30)
async def handle_start_game_click(self, chat_id, message_id, data, user_id: int):
    lobby_players = await self.app.store.game.get_lobby_players(chat_id)
    if not any(p.id == user_id for p in lobby_players):
        await self.app.store.tg_api.send_message(chat_id, "❌ Вы не были в списке игроков.")
        return

    # Mark lobby as pending (mode selection in progress)
    lobby = await self.app.store.game.get_lobby_game(chat_id)
    await self.app.store.game.update_game(lobby.id, status="pending")

    await self.app.store.tg_api.delete_message(chat_id, message_id)
    await self.app.store.tg_api.send_inline_keyboard(
        chat_id, "🎮 Выберите режим игры", build_game_mode_keyboard()
    )


@router.callback(ExitLobbyCallback)
@ratelimit(seconds=2)
async def handle_exit_lobby_click(self, chat_id: int, message_id: int, data, user_id: int):
    await handle_exit_lobby(self, chat_id, user_id, message_id)


@router.callback(JoinLobbyCallback)
async def handle_join_lobby_click(self, chat_id: int, message_id: int, data, user_id: int):
    await handle_start_game(self, chat_id, user_id, message_id)


@router.callback(FinishGameCallback)
@ratelimit(seconds=10)
async def handle_finish_game_click(self, chat_id: int, message_id: int, data, user_id: int):
    await handle_finish_game(self, chat_id, user_id)

async def handle_answer_message(self, chat_id: int, user_id: int, text: str):
    """Called from BotManager when game is in 'answering' state and user_id == choosing_user_id."""
    game = await self.app.store.game.get_active_game(chat_id)
    if not game or not game.active_question_id:
        return

    question = await self.app.store.quiz.get_question_by_id(game.active_question_id)
    if not question:
        return

    user = await self.app.store.user.get_user(user_id)
    user_name = user.display_name if user else f"ID:{user_id}"

    is_correct = text.strip().lower() in [ans.strip().lower() for ans in question.answer]
    logger.logging.info(f"{is_correct}, {text.strip().lower()}, {question.answer}")

    if not is_correct:
        is_correct = await self.app.store.quiz.llm.check_answer(question.text, question.answer, text)
    
    if is_correct:
        # Correct answer
        await self.app.store.user.increment_correct_answers(user_id)

        await self.app.store.game.add_answered_question(game.id, question.id)
        new_points = await self.app.store.game.update_player_points(user_id, question.price)
        await self.app.store.tg_api.send_message(
            chat_id,
            f'✅ Верно! Ответ: {question.answer[0]}\n'
            f"💰 +{question.price} очков. Счёт игрока {user_name}: <b>{new_points}</b>",
        )

        answered_ids = await self.app.store.game.get_answered_question_ids(game.id)
        current_categories = await self.app.store.game.get_game_categories(game.id)
        
        still_has_questions = any(
            any(q.id not in answered_ids for q in c.questions) 
            for c in current_categories
        )

        if not still_has_questions:
            players = await self.app.store.game.get_players(game.id)
            weakest_player = min(players, key=lambda p: p.points)
            
            await self.app.store.game.update_game(
                game.id,
                status=GameStatus.CHOOSING_QUESTION.value, 
                choosing_user_id=weakest_player.id,
                active_question_id=None,
            )
            await _send_category_board(self, chat_id)
            return
        
        # Winner gets to choose next question
        await self.app.store.game.update_game(
            game.id,
            status=GameStatus.CHOOSING_QUESTION.value,
            choosing_user_id=user_id,
            active_question_id=None,
        )
        await _announce_chooser(self, chat_id, user_id)
        await _send_category_board(self, chat_id)
    else:
        # Wrong answer
        logger.logging.info(f"INCORRECT ANSWER {text}")
        new_points = await self.app.store.game.update_player_points(user_id, -question.price)
        await self.app.store.tg_api.send_message(
            chat_id,
            f"❌ Неверно! Ответ игрока {user_name}: «{text.replace('>', '').replace('<', '')}»\n"
            f"💸 -{question.price} очков. Счёт: <b>{new_points}</b>\n\n"
            f"Кто ещё знает ответ?",
        )

        await self.app.store.tg_api.send_message(
        chat_id,
        f"📂 Категория: <b>{question.category.name}</b>\n"
        f"💰 Стоимость: <b>{question.price}</b>\n\n"
        f"❓ {question.text}")
        # Release the lock — button becomes active again
        await self.app.store.game.update_game(game.id, choosing_user_id=None)
        await self.app.store.tg_api.send_inline_keyboard(
            chat_id, "⚡ Кто первый?", build_answer_button()
        )

# ───────────────────────── FINAL ROUND ─────────────────────────

async def _start_final_round(self, chat_id: int, game_id: int):
    """Transition to the final round: filter players, set up bets, begin FINAL_REMOVING."""
    players = await self.app.store.game.get_players(game_id)
    eligible = [p for p in players if p.points > 0]

    if len(eligible) < 1:
        await self.app.store.tg_api.send_message(chat_id, "🏁 Финальный раунд невозможен — нет игроков с положительным счётом.")
        await _finish_game(self, chat_id, game_id)
        return

    # Kick players with <= 0 points
    for p in players:
        if p.points <= 0:
            await self.app.store.game.remove_player(p.id)
            p_user = await self.app.store.user.get_user(p.id)
            p_name = p_user.display_name if p_user else f"ID:{p.id}"
            await self.app.store.tg_api.send_message(chat_id, f"😢 {p_name} выбывает из финала (очки ≤ 0).")

    # Initialise final bet rows
    for p in eligible:
        await self.app.store.game.create_final_bet(game_id, p.id)

    # Fetch round-4 categories
    categories = await self.app.store.quiz.get_random_categories_for_round(4)
    if not categories:
        await self.app.store.tg_api.send_message(chat_id, "❌ Нет категорий для финального раунда.")
        await _finish_game(self, chat_id, game_id)
        return

    # First remover = player with highest points (most to lose goes first)
    first_remover = max(eligible, key=lambda p: p.points)
    await self.app.store.game.update_game(
        game_id,
        status=GameStatus.FINAL_REMOVING.value,
        current_round=4,
        choosing_user_id=first_remover.id,
    )

    player_lines = []
    for p in eligible:
        p_user = await self.app.store.user.get_user(p.id)
        p_name = p_user.display_name if p_user else f"ID:{p.id}"
        player_lines.append(f"• {p_name} — {p.points} очков")

    await self.app.store.tg_api.send_message(
        chat_id,
        "🏁 <b>Финальный раунд!</b>\n\nУчастники финала:\n" + "\n".join(player_lines),
    )
    await _send_final_category_board(self, chat_id, game_id)


async def _send_final_category_board(self, chat_id: int, game_id: int, message_id: int | None = None):
    """Show the category removal board for the current remover."""
    game = await self.app.store.game.get_active_game(chat_id)
    if not game:
        return

    removed = await self.app.store.game.get_final_removed_category_ids(game_id)
    all_categories = await self.app.store.quiz.get_random_categories_for_round(4)
    remaining = [c for c in all_categories if c.id not in removed]

    if len(remaining) <= 1:
        # Only one category left — move to betting
        await _start_final_betting(self, chat_id, game_id, remaining[0] if remaining else None)
        return

    remover_user = await self.app.store.user.get_user(game.choosing_user_id)
    remover_name = remover_user.display_name if remover_user else f"ID:{game.choosing_user_id}"
    text = f"🗑 <b>{remover_name}</b>, удалите одну категорию:"

    keyboard = build_final_category_remove_keyboard(remaining)
    if message_id is not None:
        await self.app.store.tg_api.edit_message(chat_id, message_id, text, keyboard)
    else:
        await self.app.store.tg_api.send_inline_keyboard(chat_id, text, keyboard)


@router.callback(FinalCategoryCallback)
@ratelimit(seconds=2)
async def handle_final_category_remove(self, chat_id: int, message_id: int, data, user_id: int):
    game = await self.app.store.game.get_active_game(chat_id)
    if not game or game.status != GameStatus.FINAL_REMOVING.value:
        return
    if game.choosing_user_id != user_id:
        return

    game_id = game.id
    await self.app.store.game.add_final_removed_category(game_id, data.category_id)

    # Check how many categories remain
    removed = await self.app.store.game.get_final_removed_category_ids(game_id)
    all_categories = await self.app.store.quiz.get_random_categories_for_round(4)
    remaining = [c for c in all_categories if c.id not in removed]

    if len(remaining) <= 1:
        # Done removing — edit the board away and start betting
        # -------------------- НЕ ЗАПУСКАЕМ СТАВКИ, ПОКА НЕ У ВСЕХ ИГРОКОВ ЧАТ С БОТОМ АКТИВЕН ЛИЧНО --------------------------
        await self.app.store.tg_api.edit_message(chat_id, message_id, "🪄 Вжух! Переходим к ставкам!", {"inline_keyboard": []})
        await _start_final_betting(self, chat_id, game_id, remaining[0] if remaining else None)
        return

    # Advance to next remover
    players = await self.app.store.game.get_players(game_id)
    player_ids = [p.id for p in players]
    current_idx = player_ids.index(user_id) if user_id in player_ids else 0
    next_remover = player_ids[(current_idx + 1) % len(player_ids)]
    await self.app.store.game.update_game(game_id, choosing_user_id=next_remover)

    await _send_final_category_board(self, chat_id, game_id, message_id=message_id)


async def _start_final_betting(self, chat_id: int, game_id: int, final_category):
    """Set status to final_betting and DM each player asking for their bet."""
    players = await self.app.store.game.get_players(game_id)

    cat_name = final_category.name if final_category else "?"
    await self.app.store.tg_api.send_message(
        chat_id,
        f"💰 <b>Финальная категория: {cat_name}</b>\n\n"
        "Каждый игрок получит вопрос в личные сообщения. Сначала сделайте ставку!",
    )

    # Store which category is the final one (in game field)
    final_q_id = None
    if final_category:
        questions = await self.app.store.quiz.list_questions(category_id=final_category.id)
        if questions:
            final_q_id = random.choice(questions).id

    await self.app.store.game.update_game(
        game_id,
        status=GameStatus.FINAL_BETTING.value,
        active_question_id=final_q_id,
        choosing_user_id=None,
    )

    for p in players:
        # In Telegram, private chat_id == user_id
        await self.app.store.tg_api.send_message(
            p.id,
            f"🏁 <b>Финальный раунд!</b>\n"
            f"Ваши очки: <b>{p.points}</b>\n\n"
            f"Введите вашу ставку (от 1 до {p.points}):",
        )


async def handle_final_bet_message(self, user_id: int, text: str):
    """Called from BotManager when status=final_betting and message is a private DM."""
    game = await self.app.store.game.get_player_active_game(user_id)
    if not game or game.status != GameStatus.FINAL_BETTING.value:
        return

    # Validate bet
    try:
        bet = int(text.strip())
    except ValueError:
        await self.app.store.tg_api.send_message(user_id, "❌ Пожалуйста, введите число.")
        return

    user = await self.app.store.user.get_user(user_id)
    max_bet = user.points if user else 0
    if bet <= 0 or bet > max_bet:
        await self.app.store.tg_api.send_message(user_id, f"❌ Ставка должна быть от 1 до {max_bet}.")
        return

    existing = await self.app.store.game.get_final_bet(game.id, user_id)
    if existing and existing.is_ready:
        await self.app.store.tg_api.send_message(user_id, "✅ Ваша ставка уже принята.")
        return

    await self.app.store.game.set_final_bet(game.id, user_id, bet)
    await self.app.store.tg_api.send_message(user_id, f"✅ Ставка принята: <b>{bet}</b> очков. Ждём остальных игроков...")

    # Check if all bets are in
    bets = await self.app.store.game.get_final_bets(game.id)
    if all(b.is_ready for b in bets):
        await _start_final_answering(self, game.chat_id, game.id)


async def _start_final_answering(self, chat_id: int, game_id: int):
    """All bets placed — send the final question to each player via DM."""
    game = await self.app.store.game.get_active_game(chat_id)
    if not game or not game.active_question_id:
        return

    question = await self.app.store.quiz.get_question_by_id(game.active_question_id)
    if not question:
        return

    await self.app.store.game.update_game(game_id, status=GameStatus.FINAL_ANSWERING.value)

    players = await self.app.store.game.get_players(game_id)
    await self.app.store.tg_api.send_message(
        chat_id,
        f"🔥 Все ставки сделаны! Вопрос финала отправлен каждому игроку в личку.\n"
        f"Категория: <b>{question.category.name}</b>",
    )

    for p in players:
        await self.app.store.tg_api.send_message(
            p.id,
            f"❓ <b>Финальный вопрос</b>\n"
            f"Категория: <b>{question.category.name}</b>\n\n"
            f"{question.text}\n\n"
            "Напишите ваш ответ:",
        )


async def handle_final_answer_message(self, user_id: int, text: str, game):
    """Called from BotManager when status=final_answering and message is a private DM."""
    game_id = game.id

    if await self.app.store.game.get_final_answer(game_id, user_id):
        await self.app.store.tg_api.send_message(user_id, "✅ Ваш ответ уже принят.")
        return

    await self.app.store.game.set_final_answer(game_id, user_id, text.strip())
    await self.app.store.tg_api.send_message(user_id, f"✅ Ответ принят: «{text.strip()}». Ждём остальных...")

    players = await self.app.store.game.get_players(game_id)
    answers = await self.app.store.game.get_final_answers(game_id)
    if len(answers) >= len(players):
        await _reveal_final(self, game.chat_id, game_id)


async def _reveal_final(self, chat_id: int, game_id: int):
    """Reveal all final answers in the group chat, update points, finish game."""
    game = await self.app.store.game.get_active_game(chat_id)
    if not game or not game.active_question_id:
        return

    question = await self.app.store.quiz.get_question_by_id(game.active_question_id)
    if not question:
        return

    bets = await self.app.store.game.get_final_bets(game_id)
    bets_by_user = {b.user_id: b.bet for b in bets}
    answers_list = await self.app.store.game.get_final_answers(game_id)
    answers = {a.user_id: a.answer for a in answers_list}

    players = await self.app.store.game.get_players(game_id)
    # Sort ASC by points — lowest reveals first (more dramatic)
    sorted_players = sorted(players, key=lambda p: p.points)

    await self.app.store.tg_api.send_message(
        chat_id,
        f"🎯 <b>Финальный вопрос</b>\n"
        f"Категория: <b>{question.category.name}</b>\n\n"
        f"❓ {question.text}\n\n"
        f'✅ Правильный ответ: <b>{question.answer[0]}</b>',
    )

    for p in sorted_players:
        p_user = await self.app.store.user.get_user(p.id)
        p_name = p_user.display_name if p_user else f"ID:{p.id}"
        bet = bets_by_user.get(p.id, 0) or 0
        player_answer = answers.get(p.id, "")
        is_correct = player_answer.strip().lower() in [ans.strip().lower() for ans in question.answer]

        if not is_correct:
            is_correct = await self.app.store.quiz.llm.check_answer(question.text, question.answer, player_answer)

        if is_correct:
            new_points = await self.app.store.game.update_player_points(p.id, bet)
            result_icon = "✅"
            delta_text = f"+{bet}"
        else:
            new_points = await self.app.store.game.update_player_points(p.id, -bet)
            result_icon = "❌"
            delta_text = f"-{bet}"

        await self.app.store.tg_api.send_message(
            chat_id,
            f"{result_icon} <b>{p_name}</b>\n"
            f"Ставка: {bet} | Ответ: «{player_answer}»\n"
            f"{delta_text} очков → итого: <b>{new_points}</b>",
        )
        await asyncio.sleep(3)

    await _finish_game(self, chat_id, game_id)


# ───────────────────────── ADMIN ─────────────────────────

@router.message("/hesoyam")
@ratelimit(seconds=10)
async def give_points(self, chat_id, user_id):
    await self.app.store.user.give_points(user_id)
    user = await self.app.store.user.get_user(user_id)
    await self.app.store.tg_api.send_message(chat_id, f"ID:{user_id} Добавлены 10000 очков! Текущий счёт: {user.points}")