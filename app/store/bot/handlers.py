import asyncio
from datetime import datetime, timezone
import random

from app.store.bot.callbacks import AnswerCallback, BackCallback, CatInBagTargetCallback, CategoryCallback, ExitLobbyCallback, FinalCategoryCallback, FinishGameCallback, FinishGameVoteCallback, GameModeCallback, JoinLobbyCallback, QuestionCallback, SearchModeCallback, StartGameCallback
from app.store.bot.router import BotRouter
from app.store.tg_api.builders import (
    GAME_BUTTONS,
    GAME_START_TEXT,
    MENU_BUTTONS,
    MENU_TEXT,
    PRIVATE_MENU_BUTTONS,
    RULES_TEXT,
    SEARCHING_BUTTONS,
    build_answer_button,
    build_category_board,
    build_final_category_remove_keyboard,
    build_game_mode_keyboard,
    build_question_keyboard,
    build_search_mode_keyboard,
)
from app.store.tg_api.game_constants import CAT_IN_BAG_CHANCE, SURR_FACES, BotButtons, BotCommands, GameModes, GameStatus, GameTimers
from app.web import logger
from app.web.utils import ratelimit

async def get_game(self, chat_id, user_id):
    if chat_id != user_id:
        game = await self.app.store.game.get_active_game(chat_id)
    else:
        game = await self.app.store.game.get_player_active_game_by_type(user_id, game_type="dm")
    return game or None

async def notify_all(self, game, text: str, inline_keyboard: dict | None = None, keyboard: dict | None = None) -> None:
    """Отправить сообщение всем игрокам игры.

    Для групповых игр — в game.chat_id.
    Для DM-игр (game_type="dm") — каждому игроку в личку через p.user_id.
    Виртуальный chat_id DM-игры нельзя использовать для отправки в Telegram —
    он нужен только для поиска игры в БД.
    """
    if game.game_type != "dm":
        if inline_keyboard:
            await self.app.store.tg_api.send_inline_keyboard(game.chat_id, text, inline_keyboard)
        elif keyboard:
            await self.app.store.tg_api.send_keyboard(game.chat_id, keyboard, text)
        else:
            await self.app.store.tg_api.send_message(game.chat_id, text)
        return

    # DM-игра — шлём каждому в личку по реальному user_id
    players = await self.app.store.game.get_players(game.id)
    for p in players:
        try:
            if inline_keyboard:
                await self.app.store.tg_api.send_inline_keyboard(p.user_id, text, inline_keyboard)
            elif keyboard:
                await self.app.store.tg_api.send_keyboard(p.user_id, keyboard, text)
            else:
                await self.app.store.tg_api.send_message(p.user_id, text)
        except Exception:
            pass


async def notify_chooser(self, game, text: str, keyboard: dict | None = None) -> None:
    """Отправить сообщение только выбирающему игроку.

    Для DM-игр — в личку choosing_user_id.
    Для групповых — в чат.
    """
    if game.game_type == "dm":
        target = game.choosing_user_id
    else:
        target = game.chat_id
    if not target:
        return
    try:
        if keyboard:
            await self.app.store.tg_api.send_inline_keyboard(target, text, keyboard)
        else:
            await self.app.store.tg_api.send_message(target, text)
    except Exception:
        pass


# ── message tracking helpers ─────────────────────────────────────────────

async def _send_temp(self, game, text: str, keyboard: dict | None = None) -> None:
    """Отправить временное сообщение и запомнить message_id для последующего удаления."""
    if game.game_type != "dm":
        resp = await self.app.store.tg_api.send_inline_keyboard(game.chat_id, text, keyboard) \
            if keyboard else await self.app.store.tg_api.send_message(game.chat_id, text)
        if resp and resp.get("ok"):
            await self.app.store.game.add_temp_message(
                game.id, resp["result"]["message_id"]
            )
    else:
        players = await self.app.store.game.get_players(game.id)
        for p in players:
            try:
                resp = await self.app.store.tg_api.send_inline_keyboard(p.user_id, text, keyboard) \
                    if keyboard else await self.app.store.tg_api.send_message(p.user_id, text)
                if resp and resp.get("ok"):
                    await self.app.store.game.add_temp_message(
                        game.id, resp["result"]["message_id"], p.user_id
                    )
            except Exception:
                pass


async def _delete_temp_and_update_board(self, game, chat_id: int) -> None:
    """Удалить все временные сообщения и обновить доску категорий."""
    rows = await self.app.store.game.get_all_temp_messages(game.id)
    for row in rows:
        target = row.user_id if (game.game_type == "dm" and row.user_id != 0) else chat_id
        try:
            await self.app.store.tg_api.delete_message(target, row.message_id)
        except Exception:
            pass
    await self.app.store.game.clear_temp_messages(game.id)
    await _send_category_board(self, chat_id, game=game)


router = BotRouter()

@router.message("/start")
@ratelimit(seconds=10, scope="user")
async def handle_start(self, chat_id: int, user_id: int):
    await self.app.store.tg_api.send_message(chat_id, "👋 Добро пожаловать в Svarme!")
    # В личке показываем меню с кнопкой поиска вместо "Начать игру"
    if chat_id == user_id:  # личный чат: chat_id == user_id в Telegram
        await self.app.store.tg_api.send_keyboard(chat_id, PRIVATE_MENU_BUTTONS, MENU_TEXT)
    else:
        await self.app.store.tg_api.send_keyboard(chat_id, MENU_BUTTONS, MENU_TEXT)

async def _send_lobby(self, chat_id: int, user_id: int, message_id: int = None):
    game = await self.app.store.game.get_lobby_game(chat_id)

    if not game:
        if message_id:
            await self.app.store.tg_api.delete_message(chat_id, message_id)
        return
    
    # if message_id:
    #     await self.app.store.game.add_lobby_message(game.id, message_id)

    lobby_players = await self.app.store.game.get_lobby_players(chat_id)
    
    player_names = []
    for p in lobby_players:
        username = p.display_name if p else f'ID:{p}'
        if p.id == game.choosing_user_id:
            player_names.insert(0, f"\n🟢 {username} 👑")
            continue
        player_names.append(f"\n🟢 {username}")
    empty_players = "\n⚪ Пусто"*(4 - len(lobby_players))
    text = f"🎮 <b>Лобби игры</b>\n"\
    f"\nРежим игры: {GameModes.BLITZ.labels if game.game_mode == GameModes.BLITZ.value else GameModes.STANDART.labels}"\
    f"\n\nИгроки:"\
    f"{''.join(player_names)}{empty_players} \n📌 Всего: {len(lobby_players)}/4"

    buttons = []
    if len(lobby_players) < 4:
        buttons.append([{"text" : "✅ Присоединиться к игре", "callback_data" : JoinLobbyCallback.prefix}])

    buttons.append([{"text" : "🚪 Покинуть лобби", "callback_data" : ExitLobbyCallback.prefix}])

    buttons.append([{"text" : GameModes.STANDART.labels, "callback_data" : GameModeCallback.create_data(game_mode=GameModes.STANDART.value)},
                    {"text" : GameModes.BLITZ.labels, "callback_data" : GameModeCallback.create_data(game_mode=GameModes.BLITZ.value)}])
    
    if len(lobby_players) >= 2:
        buttons.append([{"text" : "🚀 Старт!", "callback_data": StartGameCallback.prefix}])

    keyboard = {"inline_keyboard": buttons}

    lobby_msg_id = await self.app.store.game.get_lobby_message(game.id)

    lobby_msg_id = await self.app.store.game.get_lobby_message(game.id)
    logger.logging.info(lobby_msg_id)

    
    if lobby_msg_id:
        logger.logging.info(f"to edit {lobby_msg_id}")
        try:
            await self.app.store.tg_api.edit_message(chat_id, lobby_msg_id, text, keyboard)

        except Exception:
            await self.app.store.game.clear_lobby_message(game.id)
            lobby_msg_id= None

    if not lobby_msg_id:
        response = await self.app.store.tg_api.send_inline_keyboard(
                chat_id,
                text,
                keyboard,
            )
        if response and response.get("ok"):
            new_message_id = response["result"]["message_id"]
            await self.app.store.game.add_lobby_message(game.id, new_message_id)
            try:
                await self.app.store.tg_api.pin_chat_message(chat_id, new_message_id)
            except Exception:
                pass


@router.message(BotCommands.start_game, BotButtons.start_game, BotCommands.start_game + "@SvarMeBot")
@ratelimit(seconds=3, scope="user_chat")
async def handle_start_game(self, chat_id: int, user_id: int, message_id = None):
    # Check if game already running in this chat
    active = await self.app.store.game.get_active_game(chat_id)
    if active:
        logger.logging.info(f"active game: {active.id}, status: {active.status}")
        await self.app.store.tg_api.send_message(chat_id, "⚠️ Игра уже идёт в этом чате!")
        return

    user = await self.app.store.user.get_or_create_user(user_id)
    user_name = user.display_name if user else f"ID:{user_id}"

    lobby_players = await self.app.store.game.get_lobby_players(chat_id)
    if any(p.id == user_id for p in lobby_players):
        await self.app.store.tg_api.send_message(chat_id, f"⛔ {user_name}, ты уже в лобби!")
        return
    
    if len(lobby_players) >= 4:
        await self.app.store.tg_api.send_message(chat_id, f"❌ Максимальное количество игроков — 4. {user_name} не был добавлен в игру.")
        return
    
    await self.app.store.game.add_lobby_player(chat_id, user_id)
    lobby_players = await self.app.store.game.get_lobby_players(chat_id)

    await self.app.store.tg_api.send_message(chat_id, f"✅ {user_name} записался в игру! Ожидаем ещё игроков... ({len(lobby_players)}/4)")

    await _send_lobby(self, chat_id, user_id, message_id)
    
    

@router.message(BotCommands.exit_lobby, BotCommands.exit_lobby + "@SvarMeBot")
@ratelimit(seconds=3, scope="user_chat")
async def handle_exit_lobby(self, chat_id: int, user_id: int, message_id = None):
    game = await self.app.store.game.get_active_game(chat_id)
    if game:
        await self.app.store.tg_api.send_message(chat_id, f"❌ Игра уже идёт. Невозможно выйти из лобби")
        return
    players = await self.app.store.game.get_lobby_players(chat_id)
    user = await self.app.store.user.get_user(user_id)
    user_name = user.display_name if user else f"ID:{user_id}"

    if not any(p.id == user_id for p in players):
        await self.app.store.tg_api.send_message(chat_id, f"❌ {user_name} не в лобби")
        return
    
    lobby = await self.app.store.game.get_lobby_game(chat_id)
    lobby_msg_id = await self.app.store.game.get_lobby_message(lobby.id)

    await self.app.store.game.remove_lobby_player(chat_id, user_id)

    players = await self.app.store.game.get_lobby_players(chat_id)

    if not players or len(players) < 1:
        if lobby_msg_id:
            try:
                await self.app.store.tg_api.delete_message(chat_id, lobby_msg_id)
            except Exception:
                pass
        await self.app.store.game.clear_lobby_message(lobby.id)

    await self.app.store.tg_api.send_keyboard(chat_id, MENU_BUTTONS, f"💨 {user_name} вышел из лобби!")

    if len(players) >= 1:
        await _send_lobby(self, chat_id, user_id, message_id)

@router.message(BotCommands.stats, BotButtons.statistics, BotCommands.stats + "@SvarMeBot")
@ratelimit(seconds=10, scope="user")
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
@ratelimit(seconds=10, scope="user")
async def handle_rules(self, chat_id: int, user_id: int):
    await self.app.store.tg_api.send_message(chat_id, RULES_TEXT)

@router.message(BotCommands.menu, BotButtons.menu, BotCommands.menu + "@SvarMeBot")
@ratelimit(seconds=5, scope="user")
async def handle_menu(self, chat_id: int, user_id: int):
    await self.app.store.tg_api.send_keyboard(chat_id, MENU_BUTTONS, MENU_TEXT)

@router.message(BotCommands.finish_game, BotButtons.finish_game, BotCommands.finish_game + "@SvarMeBot")
@ratelimit(seconds=10, scope="user_chat")
async def handle_finish_game(self, chat_id: int, user_id: int):
    game = await get_game(self, chat_id, user_id)
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
    game_obj = await self.app.store.game.get_active_game(chat_id)
    if game_obj: await notify_all(self, game_obj, f"{SURR_FACES[current_votes]} {user_name} хочет сдаться.")

    if current_votes >= need_to_finish:
        if game_obj: await notify_all(self, game_obj, "‼️ <b>Голосование завершено!</b> Большинство за остановку игры.")
        await self.app.store.game.clear_finish_votes(game_id)

        players = await self.app.store.game.get_players(game_id)
        eligible = [p for p in players if p.points > 0]

        if len(eligible) < 1:
            if game_obj: await notify_all(self, game_obj, "💔 Нет ни одного игрока с положительным счётом.")

        for p in players:
            if p.points <= 0:
                await self.app.store.game.remove_player(game_id, p.user_id)

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
        await notify_all(self, game, text, inline_keyboard=keyboard)


async def _finish_game(self, chat_id: int, game_id: int):
    """Mark game finished, announce results, update statistics."""
    self.cancel_timer(game_id)
    await self.app.store.game.clear_board_messages(game_id)
    await self.app.store.game.clear_temp_messages(game_id)
    game_obj = await self.app.store.game.get_game_by_id(game_id)
    is_dm = game_obj is not None and game_obj.game_type == "dm"
    players = await self.app.store.game.get_players(game_id)
    await self.app.store.game.update_game(game_id, status=GameStatus.FINISHED.value)

    if not players:
        logger.logging.info("Игроков нет")
        if not is_dm:
            await self.app.store.tg_api.send_message(chat_id, "🏁 Игра завершена. Участников не осталось.")
            await self.app.store.tg_api.send_keyboard(chat_id, MENU_BUTTONS, MENU_TEXT)
        else:
            await notify_all(self, game_obj, "🏁 Игра завершена. Участников не осталось.")
            await notify_all(self, game_obj, MENU_TEXT, keyboard=PRIVATE_MENU_BUTTONS)
        return

    sorted_players = sorted(players, key=lambda p: p.points, reverse=True)
    winner = sorted_players[0]
    winner_user = await self.app.store.user.get_user(winner.user_id)
    winner_name = winner_user.display_name if winner_user else f"ID:{winner.user_id}"

    await self.app.store.game.update_statistics(players, winner.user_id)

    lines = ["🏁 <b>Игра завершена!</b>\n\n📊 Итоговые результаты:"]
    for i, p in enumerate(sorted_players, start=1):
        p_user = await self.app.store.user.get_user(p.user_id)
        p_name = p_user.display_name if p_user else f"ID:{p.user_id}"
        medal = {1: "🥇", 2: "🥈", 3: "🥉"}.get(i, f"{i}.")
        lines.append(f"{medal} {p_name} — <b>{p.points}</b> очков")
    lines.append(f"\n🏆 Победитель: <b>{winner_name}</b> с {winner.points} очками!")

    if is_dm:
        for p in sorted_players:
            try:
                await self.app.store.tg_api.send_message(p.user_id, "\n".join(lines))
                await self.app.store.tg_api.send_keyboard(p.user_id, PRIVATE_MENU_BUTTONS, MENU_TEXT)
            except Exception:
                pass
    else:
        await self.app.store.tg_api.send_message(chat_id, "\n".join(lines))
        await self.app.store.tg_api.send_keyboard(chat_id, MENU_BUTTONS, MENU_TEXT)


@router.message(BotCommands.surrender, BotButtons.surrender, BotCommands.surrender + "@SvarMeBot")
@ratelimit(seconds=60, scope="user_chat")
async def handle_surrender(self, chat_id: int, user_id: int):
    game = await get_game(self, chat_id, user_id)
    
    if not game:
        await self.app.store.tg_api.send_message(chat_id, "❌ Нет активной игры, в которой можно сдаться.")
        return
    
    game_chat_id = game.chat_id

    if not await self.app.store.game.is_player(game.id, user_id):
        return

    user = await self.app.store.user.get_user(user_id)
    user_name = user.display_name if user else f"ID:{user_id}"

    # Remove the surrendering player from the game
    if game: await notify_all(self, game, f"🏳 Игрок {user_name} сдался!")
    await self.app.store.game.remove_player(game.id, user_id)
    if game.game_type == "dm":
        await self.app.store.tg_api.send_keyboard(user_id, PRIVATE_MENU_BUTTONS, MENU_TEXT)

    remaining = await self.app.store.game.get_players(game.id)
    if len(remaining) <= 1:
        await _finish_game(self, game_chat_id, game.id)
    else:
        if game.choosing_user_id == user_id:
            self.cancel_timer(game.id)
            new_chooser = remaining[0].user_id
            await self.app.store.game.update_game(game.id, choosing_user_id=new_chooser, status=GameStatus.CHOOSING_QUESTION.value)
            await _announce_chooser(self, game_chat_id, new_chooser)
            await _send_category_board(self, game_chat_id)
            self.schedule_choose_timer(game.id, game_chat_id)


async def _send_category_board(self, chat_id: int, message_id: int | None = None, game=None):
    """Load 5 random round-1 categories and show the category selection board."""
    if game is None:
        game = await self.app.store.game.get_active_game(chat_id)
    if not game:
        await self.app.store.tg_api.send_message(chat_id, "❌ Нет активной игры.")
        return
    
    await asyncio.sleep(0.5)
    
    answered_ids = await self.app.store.game.get_answered_question_ids(game.id) if game else set()
    current_categories = await self.app.store.game.get_game_categories(game.id)
    is_blitz = game.game_mode == GameModes.BLITZ.value

    if not current_categories:
        count = GameModes.BLITZ.categories if is_blitz else GameModes.STANDART.categories
        current_categories = await self.app.store.quiz.get_random_categories_for_round(game.current_round if not is_blitz else 5, limit=count)

        await self.app.store.game.set_game_categories(game.id, [c.id for c in current_categories])
    
    categories = [c for c in current_categories if any(q.id not in answered_ids for q in c.questions)]

    players = await self.app.store.game.get_players(game.id)

    if not categories:
        next_round = game.current_round + 1 if game.current_round is not None else 1

        if next_round >= 4 or (is_blitz and next_round == 2):
            await _start_final_round(self, chat_id, game.id)
            return

        await self.app.store.game.update_game(game.id, current_round=next_round)
        await self.app.store.game.clear_game_categories(game.id)
        await self.app.store.game.clear_board_messages(game.id)
        await self.app.store.game.clear_temp_messages(game.id)

        game = await self.app.store.game.get_active_game(chat_id)

        players = await self.app.store.game.get_players(game.id)
        score_lines = []
        for p in players:
            p_user = await self.app.store.user.get_user(p.user_id)
            p_name = p_user.display_name if p_user else f"ID:{p.user_id}"
            score_lines.append(f"{p_name} — {p.points} очков")
        await self.app.store.tg_api.send_message(
            chat_id,
            f"🎉 <b>Раунд {next_round - 1} завершён!</b>\nПромежуточные результаты:\n" +
            "\n".join(score_lines) +
            f"\n\nПереходим к <b>раунду {next_round}!</b>",
        )
        await _announce_chooser(self, chat_id, game.choosing_user_id)

        logger.logging.info(chat_id)
        return await _send_category_board(self, chat_id, message_id)
    
    current_scores = []
    for p in players:
        p_user = await self.app.store.user.get_user(p.user_id)
        p_name = p_user.display_name if p_user else f"ID:{p.user_id}"
        
        current_scores.append(f"\n\n{'🟢' if game.choosing_user_id == p.user_id else '⚪'} {p_name} ─ ✨ Счёт: {p.points}")

    chooser_user = await self.app.store.user.get_user(game.choosing_user_id) if game.choosing_user_id else None
    chooser_name = chooser_user.display_name if chooser_user else f"ID:{game.choosing_user_id}"

    text = f"🎯 Ход <b>{chooser_name}</b> · ⏱️ {GameTimers.CHOOSE_TIMEOUT.value} сек\n\n" \
    "\n👤 Текущие игроки:" \
    f"{''.join(current_scores)}"\
    "\n\n📋 Выберите категорию:"
    keyboard = build_category_board(categories)

    if game.game_type == "dm":
        for p in players:
            stored = await self.app.store.game.get_board_message(game.id, p.user_id)
            try:
                if stored:
                    await self.app.store.tg_api.edit_message(p.user_id, stored, text, keyboard)
                else:
                    resp = await self.app.store.tg_api.send_inline_keyboard(p.user_id, text, keyboard)
                    if resp and resp.get("ok"):
                        await self.app.store.game.set_board_message(game.id, resp["result"]["message_id"], p.user_id)
            except Exception:
                try:
                    resp = await self.app.store.tg_api.send_inline_keyboard(p.user_id, text, keyboard)
                    if resp and resp.get("ok"):
                        await self.app.store.game.set_board_message(game.id, resp["result"]["message_id"], p.user_id)
                except Exception:
                    pass
    else:
        stored = message_id or await self.app.store.game.get_board_message(game.id)
        if stored:
            try:
                await self.app.store.tg_api.edit_message(chat_id, stored, text, keyboard)
                return
            except Exception:
                pass
        resp = await self.app.store.tg_api.send_inline_keyboard(chat_id, text, keyboard)
        if resp and resp.get("ok"):
            await self.app.store.game.set_board_message(game.id, resp["result"]["message_id"])

async def _announce_chooser(self, chat_id: int, choosing_user_id: int):
    # user = await self.app.store.user.get_user(choosing_user_id)
    # name = user.display_name if user else f"ID:{choosing_user_id}"
    # game = await self.app.store.game.get_active_game(chat_id)
    # if game:
    #     await notify_all(self, game,
    #         f"🎯 Ход игрока <b>{name}</b>. Выберите категорию и вопрос за ⏱️ {GameTimers.CHOOSE_TIMEOUT.value} сек:")
    pass


@router.callback(GameModeCallback)
@ratelimit(seconds=1, scope="user_chat")
async def handle_game_mode_click(self, chat_id, message_id, data, user_id: int):
    lobby_players = await self.app.store.game.get_lobby_players(chat_id)
    # if not lobby_players or len(lobby_players) < 2:
    #     await self.app.store.tg_api.send_message(chat_id, "❌ Недостаточно игроков.")
    #     return

    if not any(p.id == user_id for p in lobby_players):
        return
    
    lobby = await self.app.store.game.get_lobby_game(chat_id)

    user = await self.app.store.user.get_user(user_id)
    user_name = user.display_name if user else f"ID:{user_id}"
    vip_user = await self.app.store.user.get_user(lobby.choosing_user_id)
    vip_name = vip_user.display_name if vip_user else f"ID:{vip_user}"

    if user_id != lobby.choosing_user_id:
        # await self.app.store.tg_api.send_message(chat_id, f"❌ {user_name} не может выбрать режим. Дождитесь {vip_name}")
        return
    
    await self.app.store.game.update_game(
        lobby.id,
        game_mode=data.game_mode,
    )

    await _send_lobby(self, chat_id, user_id, message_id)


@router.callback(CategoryCallback)
@ratelimit(seconds=1, scope="user_chat")
async def handle_category_click(self, chat_id, message_id, data, user_id: int):
    game = await get_game(self, chat_id, user_id)

    if not game or game.status != GameStatus.CHOOSING_QUESTION.value:
        return
    if game.choosing_user_id != user_id:
        return

    answered_ids = await self.app.store.game.get_answered_question_ids(game.id)
    questions = await self.app.store.quiz.list_questions(category_id=data.category_id, exclude_ids=answered_ids)
    category = await self.app.store.quiz.get_category_by_id(data.category_id)
    if not questions or not category:
        return
    
    text = f"📂 Категория: <b>{category.name}</b>\n\nВыберите стоимость:"
    keyboard = build_question_keyboard(questions)

    if game.game_type == "dm":
        stored = await self.app.store.game.get_board_message(game.id, user_id)
        logger.logging.info(stored)
        if stored:
            try:
                await self.app.store.tg_api.edit_message(user_id, stored, text, keyboard)
            except Exception:
                await self.app.store.tg_api.send_inline_keyboard(user_id, text, keyboard)
        else:
            await self.app.store.tg_api.send_inline_keyboard(user_id, text, keyboard)
    else:
        await self.app.store.tg_api.edit_message(chat_id, message_id, text, keyboard)
        await self.app.store.game.set_board_message(game.id, message_id)


@router.callback(QuestionCallback)
@ratelimit(seconds=5, scope="user_chat")
async def handle_question_click(self, chat_id, message_id, data, user_id: int):
    await asyncio.sleep(0.5)
    game = await get_game(self, chat_id, user_id)
    if not game or game.status != GameStatus.CHOOSING_QUESTION.value:
        return
    if game.choosing_user_id != user_id:
        return

    question = await self.app.store.quiz.get_question_by_id(data.question_id)
    if not question:
        return

    self.cancel_timer(game.id)

    players = await self.app.store.game.get_players(game.id)
    other_players = [p for p in players if p.user_id != user_id]

    if other_players and random.random() < CAT_IN_BAG_CHANCE:
        # Сохраняем вопрос, переходим в статус выбора цели
        await self.app.store.game.update_game(
            game.id,
            active_question_id=question.id,
            status=GameStatus.CAT_IN_BAG_CHOOSING.value,
            choosing_user_id=user_id,  # кто выбрал — запомним для возврата хода
            target_user_id=None,
        )
 
        chooser_user = await self.app.store.user.get_user(user_id)
        chooser_name = chooser_user.display_name if chooser_user else f"ID:{user_id}"
 
        # Строим клавиатуру с именами других игроков
        buttons = []
        for p in other_players:
            p_user = await self.app.store.user.get_user(p.user_id)
            p_name = p_user.display_name if p_user else f"ID:{p.user_id}"
            buttons.append([{
                "text": p_name,
                "callback_data": CatInBagTargetCallback.create_data(target_user_id=p.user_id)
            }])
        keyboard = {"inline_keyboard": buttons}
 
        await notify_chooser(self, game,
            f"😼 <b>Кот в мешке!\n</b>"
            f"<b>📲 {chooser_name}</b>, выбери кому достанется этот вопрос:", keyboard)
        return

    await self.app.store.game.update_game(
        game.id,
        active_question_id=question.id,
        status=GameStatus.ANSWERING.value,
        choosing_user_id=None,
        remaining_seconds=GameTimers.ANSWER_TIMEOUT.value,
        question_asked_at=datetime.now(timezone.utc)
    )

    # Обновляем доску — убираем выбранный вопрос (редактирует существующее сообщение)
    await _send_category_board(self, chat_id, game=game)
    await _send_temp(self, game,
        f"📂 Категория: <b>{question.category.name}</b>\n"
        f"💰 Стоимость: <b>{question.price}</b>\n\n"
        f"❓ {question.text}",
    )
    await asyncio.sleep(5)
    await self.app.store.game.update_game(game.id, question_asked_at=datetime.now(timezone.utc))
    game = await get_game(self, chat_id, user_id)
    await _send_temp(self, game, "⚡ Кто первый знает ответ?"
            f"\nУ вас есть ⏱️ {game.remaining_seconds} сек", build_answer_button())
    self.schedule_answer_button_timer(game.id, chat_id)


@router.callback(AnswerCallback)
@ratelimit(seconds=2, scope="user_chat")
async def handle_answer_button_click(self, chat_id, message_id, data, user_id: int):
    user = await self.app.store.user.get_user(user_id)
    name = user.display_name if user else f"ID:{user_id}"
    game = await self.app.store.game.get_active_game(chat_id)

    if not game or game.status != GameStatus.ANSWERING.value:
        return
    
    self.cancel_timer(game.id)

    if not await self.app.store.game.is_player(game.id, user_id):
        return
    if game.choosing_user_id is not None:
        # Someone already claimed the answer slot
        return

    # Calculate how many seconds remain from the answer-button window
    elapsed = 0.0
    now = datetime.now(timezone.utc)
    if game.question_asked_at:
        elapsed = (now - game.question_asked_at.replace(tzinfo=timezone.utc)).total_seconds()
    seconds_left = max(game.remaining_seconds - elapsed, 0)

    # Lock the answerer and save remaining seconds
    self.cancel_timer(game.id) 
    await self.app.store.game.update_game(game.id, choosing_user_id=user_id, remaining_seconds=int(seconds_left), question_asked_at=now)

    # Удаляем кнопку (она в temp) — через стандартный delete, в БД она уже есть
    try:
        await self.app.store.tg_api.delete_message(chat_id, message_id)
    except Exception:
        pass
    await _send_temp(self, game, f"✋ Отвечает <b>{name}</b>! Напишите ваш ответ за ⏱ {GameTimers.ANSWERING_TIMEOUT.value} сек:")

    self.schedule_answering_timer(game.id, chat_id, GameTimers.ANSWERING_TIMEOUT.value)


@router.callback(BackCallback)
@ratelimit(seconds=1, scope="user_chat")
async def handle_back_click(self, chat_id, message_id, data, user_id: int):
    game = await get_game(self, chat_id, user_id)
    if game and game.choosing_user_id != user_id:
        return
    if game:
        uid = user_id if game.game_type == "dm" else 0
        await self.app.store.game.set_board_message(game.id, message_id, uid)
    await _send_category_board(self, chat_id, game=game)


@router.callback(StartGameCallback)
@ratelimit(seconds=2, scope="user_chat")
async def handle_start_game_click(self, chat_id, message_id, data, user_id: int):
    lobby_players = await self.app.store.game.get_lobby_players(chat_id)
    user = await self.app.store.user.get_user(user_id)
    user_name = user.display_name if user else f"ID:{user_id}"

    if not any(p.id == user_id for p in lobby_players):
        # await self.app.store.tg_api.send_message(chat_id, f"❌ {user_name} не был в списке игроков.")
        return

    game = await self.app.store.game.get_lobby_game(chat_id)
    vip_user = await self.app.store.user.get_user(game.choosing_user_id)
    vip_name = vip_user.display_name if vip_user else f"ID:{vip_user}"

    if not game:
        await self.app.store.tg_api.send_message(chat_id, "❌ Игра не создана.")
        return
    
    if game.choosing_user_id != user_id:
        # await self.app.store.tg_api.send_message(chat_id, f"❌ {user_name} не может запустить игру. Дождитесь {vip_name}")
        return
    

    # Mark lobby as pending (mode selection in progress)
    lobby = await self.app.store.game.get_lobby_game(chat_id)
    lobby_msg_id = await self.app.store.game.get_lobby_message(lobby.id)
    if lobby_msg_id:
        await self.app.store.tg_api.delete_message(chat_id, lobby_msg_id)

        await self.app.store.game.clear_lobby_message(lobby.id)

    game = lobby
    player_ids = [p.id for p in lobby_players]

    choosing_user_id = random.choice(player_ids)
    await self.app.store.game.update_game(game.id, choosing_user_id=choosing_user_id, status=GameStatus.CHOOSING_QUESTION.value)

    await self.app.store.tg_api.send_keyboard(chat_id, GAME_BUTTONS, GAME_START_TEXT)
    await _announce_chooser(self, chat_id, choosing_user_id)
    await _send_category_board(self, chat_id)
    self.schedule_choose_timer(game.id, chat_id)

    # await self.app.store.game.update_game(lobby.id, status="pending")

    # await self.app.store.tg_api.send_inline_keyboard(
    #     chat_id, "🎮 Выберите режим игры", build_game_mode_keyboard()
    # )


@router.callback(ExitLobbyCallback)
@ratelimit(seconds=2, scope="user_chat")
async def handle_exit_lobby_click(self, chat_id: int, message_id: int, data, user_id: int):
    await handle_exit_lobby(self, chat_id, user_id, message_id)


@router.callback(JoinLobbyCallback)
@ratelimit(seconds=2, scope="user_chat")
async def handle_join_lobby_click(self, chat_id: int, message_id: int, data, user_id: int):
    await handle_start_game(self, chat_id, user_id, message_id)


@router.callback(FinishGameCallback)
@ratelimit(seconds=2, scope="user_chat")
async def handle_finish_game_click(self, chat_id: int, message_id: int, data, user_id: int):
    await handle_finish_game(self, chat_id, user_id)

async def _is_still_has_questions(self, game_id: int):
    answered_ids = await self.app.store.game.get_answered_question_ids(game_id)
    current_categories = await self.app.store.game.get_game_categories(game_id)

    return any(
        any(q.id not in answered_ids for q in c.questions)
        for c in current_categories
    )

async def handle_answer_message(self, chat_id: int, user_id: int, text: str, message_id : int | None = None):
    """Called from BotManager when game is in 'answering' state and user_id == choosing_user_id."""
    game = await get_game(self, chat_id, user_id)
    if not game or not game.active_question_id:
        return
    
    if message_id:
        uid = user_id if game.game_type == "dm" else 0
        await self.app.store.game.add_temp_message(game.id, message_id, uid)

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
        # Correct answer — cancel any running timer immediately
        self.cancel_timer(game.id)
        await self.app.store.user.increment_correct_answers(user_id)

        await self.app.store.game.add_answered_question(game.id, question.id)
        new_points = await self.app.store.game.update_player_points(game.id, user_id, question.price)
        await _send_temp(self, game,
            f'✅ Верно! Ответ: {question.answer[0]}\n'
            f"💰 +{question.price} очков. Счёт игрока {user_name}: <b>{new_points}</b>",
        )
        await asyncio.sleep(3)

        still_has_questions = await _is_still_has_questions(self, game.id)

        if not still_has_questions:
            players = await self.app.store.game.get_players(game.id)
            weakest_player = min(players, key=lambda p: p.points)
            await self.app.store.game.update_game(
                game.id,
                status=GameStatus.CHOOSING_QUESTION.value,
                choosing_user_id=weakest_player.user_id,
                active_question_id=None,
            )
            await _delete_temp_and_update_board(self, game, chat_id)
            self.schedule_choose_timer(game.id, chat_id)
            return

        await self.app.store.game.update_game(
            game.id,
            status=GameStatus.CHOOSING_QUESTION.value,
            choosing_user_id=user_id,
            active_question_id=None,
        )
        await _announce_chooser(self, chat_id, user_id)
        await _delete_temp_and_update_board(self, game, chat_id)
        self.schedule_choose_timer(game.id, chat_id)
    else:
        # Wrong answer — resume remaining time on answer button
        new_points = await self.app.store.game.update_player_points(game.id, user_id, -question.price)
        await _send_temp(self, game,
            f"❌ Неверно! Ответ игрока {user_name}: «{text.replace('>', '').replace('<', '')}»\n"
            f"💸 -{question.price} очков. Счёт: <b>{new_points}</b>\n\n",
        )
        # При неверном ответе НЕ удаляем temp — вопрос остаётся, кнопка возвращается
        await _resume_button_timer(self, game.id, chat_id)

        await self.app.store.game.update_game(game.id, choosing_user_id=None)
        await _send_temp(self, game, "⚡ Кто первый знает ответ?"
            f"\nУ вас есть ⏱️ {game.remaining_seconds} сек", build_answer_button())

# ------------------------- Cat in Bag --------------------------------

@router.callback(CatInBagTargetCallback)
@ratelimit(seconds=2, scope="user_chat")
async def handle_cat_in_bag_target_click(self, chat_id: int, message_id: int, data, user_id: int):
    """Выбирающий нажал на игрока — передаём ему вопрос."""
    game = await get_game(self, chat_id, user_id)
    if not game or game.status != GameStatus.CAT_IN_BAG_CHOOSING.value:
        logger.logging.info(game.status)
        return
    if game.choosing_user_id != user_id:
        return
 
    question = await self.app.store.quiz.get_question_by_id(game.active_question_id)
    if not question:
        return
 
    target_user = await self.app.store.user.get_user(data.target_user_id)
    target_name = target_user.display_name if target_user else f"ID:{data.target_user_id}"
 
    await self.app.store.game.update_game(
        game.id,
        status=GameStatus.CAT_IN_BAG.value,
        target_user_id=data.target_user_id,
        remaining_seconds=GameTimers.ANSWERING_TIMEOUT.value,
        question_asked_at=datetime.now(timezone.utc),
    )
 
    question_text = (
        f"😼 <b>Кот в мешке!</b>\n\n"
        f"📂 Категория: <b>{question.category.name}</b>\n"
        f"💰 Стоимость: <b>{question.price}</b>\n"
        f"❓ {question.text}\n\n"
        f"⏱ Отвечает <b>{target_name}</b>! Напишите ответ за {GameTimers.ANSWERING_TIMEOUT.value} сек:"
    )
 
    if game.game_type == "dm":
        try:
            await self.app.store.tg_api.delete_message(user_id, message_id)
        except Exception:
            pass
        await _send_temp(self, game, question_text)
    else:
        resp = await self.app.store.tg_api.edit_message(
            chat_id, message_id, question_text, {"inline_keyboard": []}
        )
        if resp and resp.get("ok"):
            await self.app.store.game.add_temp_message(game.id, resp["result"]["message_id"])
        else:
            await self.app.store.game.add_temp_message(game.id, message_id)
 
    self.schedule_answering_timer(game.id, chat_id, GameTimers.ANSWERING_TIMEOUT.value)

async def handle_cat_in_bag_answer(self, chat_id: int, user_id: int, text: str, message_id: int | None = None):
    """Вызывается когда target_user_id отвечает на вопрос кота в мешке."""
    game = await self.app.store.game.get_active_game(chat_id)
    if not game or not game.active_question_id:
        return
    if game.status != GameStatus.CAT_IN_BAG.value:
        return
    if game.target_user_id != user_id:
        return
    
    if message_id:
        uid = user_id if game.game_type == "dm" else 0
        await self.app.store.game.add_temp_message(game.id, message_id, uid)
 
    self.cancel_timer(game.id)
 
    question = await self.app.store.quiz.get_question_by_id(game.active_question_id)
    if not question:
        return
 
    user = await self.app.store.user.get_user(user_id)
    user_name = user.display_name if user else f"ID:{user_id}"
 
    is_correct = text.strip().lower() in [ans.strip().lower() for ans in question.answer]
    if not is_correct:
        is_correct = await self.app.store.quiz.llm.check_answer(question.text, question.answer, text)
 
    await self.app.store.game.add_answered_question(game.id, question.id)
 
    if is_correct:
        await self.app.store.user.increment_correct_answers(user_id)
        new_points = await self.app.store.game.update_player_points(game.id, user_id, question.price)
        await _send_temp(self, game,
            f'✅ Верно! Ответ: {question.answer[0]}\n'
            f"💰 +{question.price} очков. Счёт игрока {user_name}: <b>{new_points}</b>",
        )
    else:
        new_points = await self.app.store.game.update_player_points(game.id, user_id, -question.price)
        await _send_temp(self, game,
            f"❌ Неверно! Ответ игрока {user_name}: «{text.replace('>', '').replace('<', '')}»\n"
            f"💸 -{question.price} очков. Счёт: <b>{new_points}</b>\n\n",
        )

    await asyncio.sleep(3)
    chooser_id = game.choosing_user_id
    await self.app.store.game.update_game(
        game.id,
        status=GameStatus.CHOOSING_QUESTION.value,
        choosing_user_id=chooser_id,
        target_user_id=None,
        active_question_id=None,
    )
    await _announce_chooser(self, chat_id, chooser_id)
    await _delete_temp_and_update_board(self, game, chat_id)
    self.schedule_choose_timer(game.id, chat_id)

# ───────────────────────── FINAL ROUND ─────────────────────────

async def _start_final_round(self, chat_id: int, game_id: int):
    """Transition to the final round: filter players, set up bets, begin FINAL_REMOVING."""
    players = await self.app.store.game.get_players(game_id)
    eligible = [p for p in players if p.points > 0]
 
    # Kick players with <= 0 points
    for p in players:
        if p.points <= 0:
            await self.app.store.game.remove_player(game_id, p.user_id)
            p_user = await self.app.store.user.get_user(p.user_id)
            p_name = p_user.display_name if p_user else f"ID:{p.user_id}"
            game_tmp = await self.app.store.game.get_game_by_id(game_id)
            if game_tmp: await notify_all(self, game_tmp, f"😢 {p_name} выбывает из финала (очки ≤ 0).")
 
    players = await self.app.store.game.get_players(game_id)
    # Загружаем game один раз — нужен для notify_all
    game_obj = await self.app.store.game.get_game_by_id(game_id)
 
    if len(players) <= 1:
        if game_obj:
            await notify_all(self, game_obj, "🏁 Финальный раунд невозможен — недостаточно игроков с положительным счётом.")
        await _finish_game(self, chat_id, game_id)
        return
 
    # Initialise final bet rows
    for p in eligible:
        await self.app.store.game.create_final_bet(game_id, p.user_id)
 
    # Fetch round-4 categories
    categories = await self.app.store.quiz.get_random_categories_for_round(4)
    if not categories:
        if game_obj:
            await notify_all(self, game_obj, "❌ Нет категорий для финального раунда.")
        await _finish_game(self, chat_id, game_id)
        return
 
    # First remover = player with highest points (most to lose goes first)
    first_remover = max(eligible, key=lambda p: p.points)
    await self.app.store.game.update_game(
        game_id,
        status=GameStatus.FINAL_REMOVING.value,
        current_round=4,
        choosing_user_id=first_remover.user_id,
    )
 
    player_lines = []
    for p in eligible:
        p_user = await self.app.store.user.get_user(p.user_id)
        p_name = p_user.display_name if p_user else f"ID:{p.user_id}"
        player_lines.append(f"• {p_name} — {p.points} очков")
 
    if game_obj:
        await notify_all(self, game_obj, "🏁 <b>Финальный раунд!</b>\n\nУчастники финала:\n" + "\n".join(player_lines))
    await _send_final_category_board(self, chat_id, game_id)
 
 
async def _send_final_category_board(self, chat_id: int, game_id: int, message_id: int | None = None):
    """Show the category removal board.
    Все игроки видят список оставшихся категорий.
    Кнопки удаления — только у текущего remover.
    message_id каждого игрока хранится в board_messages (user_id=-1-p.user_id для финала).
    """
    game = await self.app.store.game.get_game_by_id(game_id)
    if not game:
        return
 
    removed = await self.app.store.game.get_final_removed_category_ids(game_id)
    all_categories = await self.app.store.quiz.get_random_categories_for_round(4)
    remaining = [c for c in all_categories if c.id not in removed]
 
    if len(remaining) <= 1:
        await _start_final_betting(self, chat_id, game_id, remaining[0] if remaining else None)
        return
 
    remover_user = await self.app.store.user.get_user(game.choosing_user_id)
    remover_name = remover_user.display_name if remover_user else f"ID:{game.choosing_user_id}"
    keyboard_with_buttons = build_final_category_remove_keyboard(remaining)
    keyboard_empty = {"inline_keyboard": []}
 
    # Текст одинаковый для всех — список категорий + кто удаляет
    cats_list = "\n".join(f"• {c.name}" for c in remaining)
    text_for_remover = (
        f"🗑 <b>{remover_name}</b>, ваш ход — удалите одну категорию:\n\n"
        f"{cats_list}"
    )
    text_for_others = (
        f"🗑 Ход <b>{remover_name}</b> — удаляет категорию\n\n"
        f"Оставшиеся категории:\n{cats_list}"
    )
 
    if game.game_type == "dm":
        players = await self.app.store.game.get_players(game_id)
        for p in players:
            is_remover = (p.user_id == game.choosing_user_id)
            text = text_for_remover if is_remover else text_for_others
            kb = keyboard_with_buttons if is_remover else keyboard_empty
            # Ключ для хранения: отрицательный user_id чтобы не пересекаться с доской категорий
            store_key = -(p.user_id)
            stored = await self.app.store.game.get_board_message(game_id, store_key)
            try:
                if stored:
                    await self.app.store.tg_api.edit_message(p.user_id, stored, text, kb)
                else:
                    resp = await self.app.store.tg_api.send_inline_keyboard(p.user_id, text, kb)
                    if resp and resp.get("ok"):
                        await self.app.store.game.set_board_message(
                            game_id, resp["result"]["message_id"], store_key
                        )
            except Exception:
                try:
                    resp = await self.app.store.tg_api.send_inline_keyboard(p.user_id, text, kb)
                    if resp and resp.get("ok"):
                        await self.app.store.game.set_board_message(
                            game_id, resp["result"]["message_id"], store_key
                        )
                except Exception:
                    pass
    else:
        stored = message_id or await self.app.store.game.get_board_message(game_id, -1)
        try:
            if stored:
                await self.app.store.tg_api.edit_message(chat_id, stored, text_for_remover, keyboard_with_buttons)
                if not message_id:
                    pass  # уже сохранено
                else:
                    await self.app.store.game.set_board_message(game_id, stored, -1)
                return
        except Exception:
            stored = None
        resp = await self.app.store.tg_api.send_inline_keyboard(chat_id, text_for_remover, keyboard_with_buttons)
        if resp and resp.get("ok"):
            await self.app.store.game.set_board_message(game_id, resp["result"]["message_id"], -1)
 
 
@router.callback(FinalCategoryCallback)
@ratelimit(seconds=2, scope="user_chat")
async def handle_final_category_remove(self, chat_id: int, message_id: int, data, user_id: int):
    game = await get_game(self, chat_id, user_id)
    if not game or game.status != GameStatus.FINAL_REMOVING.value:
        return
    if game.choosing_user_id != user_id:
        return
 
    game_id = game.id
    await self.app.store.game.add_final_removed_category(game_id, data.category_id)
 
    removed = await self.app.store.game.get_final_removed_category_ids(game_id)
    all_categories = await self.app.store.quiz.get_random_categories_for_round(4)
    remaining = [c for c in all_categories if c.id not in removed]
 
    if len(remaining) <= 1:
        # Редактируем сообщение у chooser, переходим к ставкам
        try:
            target = user_id if game.game_type == "dm" else chat_id
            await self.app.store.tg_api.edit_message(target, message_id, "🪄 Вжух! Переходим к ставкам!", {"inline_keyboard": []})
        except Exception:
            pass
        await _start_final_betting(self, game.chat_id, game_id, remaining[0] if remaining else None)
        return
 
    players = await self.app.store.game.get_players(game_id)
    player_ids = [p.user_id for p in players]
    current_idx = player_ids.index(user_id) if user_id in player_ids else 0
    next_remover = player_ids[(current_idx + 1) % len(player_ids)]
    await self.app.store.game.update_game(game_id, choosing_user_id=next_remover)
 
    # message_id хранится в board_messages — передавать не нужно
    await _send_final_category_board(self, game.chat_id, game_id)
 
 
async def _start_final_betting(self, chat_id: int, game_id: int, final_category):
    """Set status to final_betting and DM each player asking for their bet."""
    players = await self.app.store.game.get_players(game_id)
 
    cat_name = final_category.name if final_category else "?"
    game_bet = await self.app.store.game.get_game_by_id(game_id)
    if game_bet:
        await notify_all(self, game_bet,
            f"💰 <b>Финальная категория: {cat_name}</b>\n\n"
            "Каждый игрок получит вопрос в личные сообщения.\n⚠️ Сначала сделайте ставку!",
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
        # Перечитываем очки — p может быть detached с устаревшим значением
        fresh = await self.app.store.game.get_player(game_id, p.user_id)
        points = fresh.points if fresh else p.points
        await self.app.store.tg_api.send_message(
            p.user_id,
            f"🏁 <b>Финальный раунд!</b>\n"
            f"Ваши очки: <b>{points}</b>\n\n"
            f"Введите вашу ставку (от 1 до {points}):",
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
 
    player = await self.app.store.game.get_player(game.id, user_id)
    max_bet = player.points if player else 0
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
    game = await self.app.store.game.get_game_by_id(game_id)
    if not game or not game.active_question_id:
        return
 
    question = await self.app.store.quiz.get_question_by_id(game.active_question_id)
    if not question:
        return
 
    await self.app.store.game.update_game(game_id, status=GameStatus.FINAL_ANSWERING.value)
 
    players = await self.app.store.game.get_players(game_id)
    if game.game_type != "dm":
        await self.app.store.tg_api.send_message(
            chat_id,
            f"🔥 Все ставки сделаны! Вопрос финала отправлен каждому игроку в личку.\n"
            f"📂 Категория: <b>{question.category.name}</b>",
        )
 
    # Финальный вопрос всегда идёт в личку каждому
    for p in players:
        await self.app.store.tg_api.send_message(
            p.user_id,
            f"📢 <b>Финальный вопрос</b>\n"
            f"📂 Категория: <b>{question.category.name}</b>\n\n"
            f"❓ {question.text}\n\n"
            "📝 Напишите ваш ответ:",
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
    """Reveal all final answers, update points, finish game."""
    game = await self.app.store.game.get_game_by_id(game_id)
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
    sorted_players = sorted(players, key=lambda p: p.points)
 
    await notify_all(self, game,
        f"🎯 <b>Финальный вопрос</b>\n"
        f"📂 Категория: <b>{question.category.name}</b>\n\n"
        f"❓ {question.text}\n\n"
        f'✅ Правильный ответ: <b>{question.answer[0]}</b>',
    )
 
    await asyncio.sleep(3)
 
    for p in sorted_players:
        p_user = await self.app.store.user.get_user(p.user_id)
        p_name = p_user.display_name if p_user else f"ID:{p.user_id}"
        bet = bets_by_user.get(p.user_id, 0) or 0
        player_answer = answers.get(p.user_id, "")
        is_correct = player_answer.strip().lower() in [ans.strip().lower() for ans in question.answer]
 
        if not is_correct:
            is_correct = await self.app.store.quiz.llm.check_answer(question.text, question.answer, player_answer)
 
        if is_correct:
            new_points = await self.app.store.game.update_player_points(game_id, p.user_id, bet)
            result_icon = "✅"
            delta_text = f"+{bet}"
        else:
            new_points = await self.app.store.game.update_player_points(game_id, p.user_id, -bet)
            result_icon = "❌"
            delta_text = f"-{bet}"
 
        await notify_all(self, game,
            f"{result_icon} <b>{p_name}</b>\n"
            f"Ставка: {bet} | Ответ: «{player_answer}»\n"
            f"{delta_text} очков → итого: <b>{new_points}</b>",
        )
        await asyncio.sleep(3)
 
    await _finish_game(self, game.chat_id, game_id)


# ───────────────────────── TIMERS ─────────────────────────

async def _resume_button_timer(self, game_id: int, chat_id: int):
    game = await self.app.store.game.get_active_game(chat_id)
    
    remaining = game.remaining_seconds or GameTimers.ANSWER_TIMEOUT.value
    
    if remaining > 0.5:
        await self.app.store.game.update_game(
            game_id,
            question_asked_at=datetime.now(timezone.utc)
        )
        self.schedule_answer_button_timer(game_id, chat_id, remaining)
    else:
        # Если пока игрок думал, общее время вышло — закрываем вопрос
        await _on_answer_button_timeout(self, game_id, chat_id, 0)

async def _on_choose_timeout(self, game_id: int, chat_id: int, seconds: float):
    """Fired when chooser didn't pick a question in time — pick random question."""
    try:
        await asyncio.sleep(seconds)

        game = await self.app.store.game.get_active_game(chat_id)
        if not game or game.id != game_id or game.status != GameStatus.CHOOSING_QUESTION.value:
            return

        # Collect all unanswered questions across current categories
        answered_ids = await self.app.store.game.get_answered_question_ids(game_id)
        current_categories = await self.app.store.game.get_game_categories(game_id)
        available = [
            q for c in current_categories for q in c.questions if q.id not in answered_ids
        ]
        if not available:
            return

        question = random.choice(available)

        await _send_temp(self, game,
            f"⏰ Время вышло! Выбираю случайный вопрос...\n\n"
            f"📂 Категория: <b>{question.category.name}</b>\n"
            f"💰 Стоимость: <b>{question.price}</b>\n\n"
            f"❓ {question.text}",
        )

        await self.app.store.game.update_game(
            game_id,
            active_question_id=question.id,
            status=GameStatus.ANSWERING.value,
            choosing_user_id=None,
        )

        # await asyncio.sleep(3)
        from datetime import datetime, timezone
        await self.app.store.game.update_game(game_id, question_asked_at=datetime.now(timezone.utc), remaining_seconds=GameTimers.ANSWER_TIMEOUT.value)
        game = await self.app.store.game.get_active_game(chat_id)
        await _send_temp(self, game, "⚡ Кто первый знает ответ?"
            f"\nУ вас есть ⏱️ {game.remaining_seconds} сек", build_answer_button())
        self.schedule_answer_button_timer(game_id, chat_id)

    except Exception as e:
        logger.logging.error(f"Error in _on_choose_timeout for game {game_id}: {e}", exc_info=True)

async def _on_answer_button_timeout(self, game_id: int, chat_id: int, seconds: float):
    """Fired when nobody pressed the answer button in time — reveal answer, same chooser picks again."""
    try:
        await asyncio.sleep(seconds)

        game = await self.app.store.game.get_active_game(chat_id)
        if not game or game.id != game_id or game.status != GameStatus.ANSWERING.value:
            return
        # Only fire if nobody has locked in yet
        if game.choosing_user_id is not None:
            return

        question = await self.app.store.quiz.get_question_by_id(game.active_question_id)
        if not question:
            return

        await self.app.store.game.add_answered_question(game_id, question.id)
        await _send_temp(self, game,
            f"⏰ Никто не ответил!\n"
            f'✅ Правильный ответ: <b>{question.answer[0]}</b>',
        )
        await asyncio.sleep(3)

        game = await self.app.store.game.get_active_game(chat_id)
        if not game or game.id != game_id:
            return

        players = await self.app.store.game.get_players(game_id)
        if not players:
            return

        fresh_players = []
        for p in players:
            fresh = await self.app.store.game.get_player(game_id, p.user_id)
            if fresh:
                fresh_players.append(fresh)
        if not fresh_players:
            return
 
        chooser_id = min(fresh_players, key=lambda p: p.points).user_id
        await self.app.store.game.update_game(
            game_id,
            status=GameStatus.CHOOSING_QUESTION.value,
            choosing_user_id=chooser_id,
            active_question_id=None,
        )
 
        # Перезагружаем game с новым choosing_user_id для правильной отрисовки доски
        game = await self.app.store.game.get_active_game(chat_id)
        if not game:
            return
 
        await _delete_temp_and_update_board(self, game, chat_id)
        self.schedule_choose_timer(game_id, chat_id)

    except Exception as e:
        logger.logging.error(f"Error in _on_choose_timeout for game {game_id}: {e}", exc_info=True)

async def _on_answering_timeout(self, game_id: int, chat_id: int, seconds: float):
    """Fired when locked-in player didn't type answer in time — reveal answer, same chooser picks again."""
    try:
        await asyncio.sleep(seconds)
 
        game = await self.app.store.game.get_active_game(chat_id)
        if not game or game.id != game_id:
            return
 
        # Таймаут кота в мешке
        if game.status == GameStatus.CAT_IN_BAG.value:
            question = await self.app.store.quiz.get_question_by_id(game.active_question_id)
            if not question:
                return
            timed_out_user = await self.app.store.user.get_user(game.target_user_id)
            timed_out_name = timed_out_user.display_name if timed_out_user else f"ID:{game.target_user_id}"
            new_points = await self.app.store.game.update_player_points(game_id, game.target_user_id, -question.price)
            await self.app.store.game.add_answered_question(game_id, question.id)
            await _send_temp(self, game,
                f"⏰ <b>{timed_out_name}</b> не успел ответить на вопрос!"
                f"✅ Правильный ответ: {question.answer[0]}"
                f"💸 -{question.price} очков. Счёт: <b>{new_points}</b>",
            )
            await asyncio.sleep(3)
            chooser_id = game.choosing_user_id
            await self.app.store.game.update_game(
                game_id,
                status=GameStatus.CHOOSING_QUESTION.value,
                choosing_user_id=chooser_id,
                target_user_id=None,
                active_question_id=None,
            )
            await _announce_chooser(self, chat_id, chooser_id)
            await _delete_temp_and_update_board(self, game, chat_id)
            self.schedule_choose_timer(game_id, chat_id)
            return
 
        if game.status != GameStatus.ANSWERING.value:
            return
        if game.choosing_user_id is None:
            return
 
        question = await self.app.store.quiz.get_question_by_id(game.active_question_id)
        if not question:
            return
 
        timed_out_user = await self.app.store.user.get_user(game.choosing_user_id)
        timed_out_name = timed_out_user.display_name if timed_out_user else f"ID:{game.choosing_user_id}"
 
        new_points = await self.app.store.game.update_player_points(game_id, game.choosing_user_id, -question.price)
        await self.app.store.game.add_answered_question(game_id, question.id)
 
        await _send_temp(self, game,
            f"⏰ {timed_out_name} не успел ответить!\n"
            f"💸 -{question.price} очков. Счёт: <b>{new_points}</b>\n\n"
        )
        # Не удаляем temp — вопрос остаётся, кнопка возвращается
        await self.app.store.game.update_game(game_id, choosing_user_id=None)
        await _send_temp(self, game, "⚡ Кнопка снова активна! Кто первый?"
            f"\nОсталось ⏱ {game.remaining_seconds} сек", build_answer_button())
        await _resume_button_timer(self, game_id, chat_id)
 
    except Exception as e:
        logger.logging.error(f"Error in _on_choose_timeout for game {game_id}: {e}", exc_info=True)


# ───────────────────────── ADMIN ─────────────────────────

@router.message("/hesoyam")
@ratelimit(seconds=10, scope="user_chat")
async def give_points(self, chat_id, user_id):
    game = await self.app.store.game.get_active_game(chat_id)
    if not game:
        await self.app.store.tg_api.send_message(chat_id, "❌ Нет активной игры.")
        return
    
    points = await self.app.store.game.update_player_points(game.id, user_id, 10000)
    await self.app.store.tg_api.send_message(chat_id, f"ID:{user_id} Добавлены 10000 очков! Текущий счёт: {points}")

# @router.message("/delete_all_active_games")
# @ratelimit(seconds=15, scope="chat")
# async def delete_all_active_games(self, chat_id, user_id):
#     await self.app.store.tg_api.send_message(chat_id, "Удаление всех активных игр")
#     await self.app.store.game.delete_active_games()



# ───────────────────────── MATCHMAKING ─────────────────────────

def _build_search_text(mode_label: str, queue_size: int) -> str:
    return (
        f"🔍 <b>Поиск игры — {mode_label}</b>\n\n"
        f"🌐 Игроков в очереди: {queue_size}\n\n"
        f"🎲 Игра начнётся, когда будет минимум 2 игрока\n\n"
        f"✏️ Введите /cancel_search чтобы отменить."
    )

@router.message(BotCommands.search, BotButtons.search)
@ratelimit(seconds=5, scope="user")
async def handle_search(self, chat_id: int, user_id: int):
    """/search — показать выбор режима. Только в личке."""
    # Проверяем что не в активной игре
    active_game = await self.app.store.game.get_player_active_game(user_id)
    if active_game:
        await self.app.store.tg_api.send_message(
            chat_id, "❌ Ты уже участвуешь в игре. Сначала заверши её."
        )
        return

    # Проверяем что не уже в очереди
    entry = await self.app.store.matchmaking.is_in_queue(user_id)
    if entry:
        from app.store.tg_api.game_constants import GameModes
        mode_label = next(
            (m.labels for m in GameModes if m.value == entry.game_mode), entry.game_mode
        )
        queue = await self.app.store.matchmaking.get_queue(entry.game_mode)
        pos = next((i + 1 for i, e in enumerate(queue) if e.user_id == user_id), "?")
        await self.app.store.tg_api.send_message(
            chat_id,
            f"⏳ Вы уже в очереди — режим {mode_label} (позиция {pos}/{len(queue)}).\n"
            f"Нажмите «{BotButtons.cancel_search}» чтобы выйти.",
        )
        return

    # Показываем выбор режима
    await self.app.store.tg_api.send_inline_keyboard(
        chat_id,
        "🔍 <b>Поиск игры</b>\n\nВыберите режим:",
        build_search_mode_keyboard(),
    )


@router.callback(SearchModeCallback)
@ratelimit(seconds=3, scope="user")
async def handle_search_mode_click(self, chat_id: int, message_id: int, data, user_id: int):
    """Игрок выбрал режим — ставим в очередь."""
    from app.store.tg_api.game_constants import GameModes
    from app.store.tg_api.builders import SEARCHING_BUTTONS
 
    active_game = await self.app.store.game.get_player_active_game(user_id)
    if active_game:
        await self.app.store.tg_api.edit_message(
            chat_id, message_id, "❌ Ты уже в игре.", {"inline_keyboard": []}
        )
        return
 
    added = await self.app.store.matchmaking.add_to_queue(user_id, data.game_mode)
    mode_label = next(
        (m.labels for m in GameModes if m.value == data.game_mode), data.game_mode
    )
 
    if not added:
        await self.app.store.tg_api.edit_message(
            chat_id, message_id,
            f"⏳ Ты уже в очереди — режим {mode_label}.",
            {"inline_keyboard": []},
        )
        return
 
    queue = await self.app.store.matchmaking.get_queue(data.game_mode)
    search_text = _build_search_text(mode_label, len(queue))
    await self.app.store.tg_api.edit_message(chat_id, message_id, search_text, {"inline_keyboard": []})
    # Сохраняем message_id чтобы обновлять его когда меняется очередь
    await self.app.store.matchmaking.set_search_message(user_id, message_id)
    # Переключаем клавиатуру на "режим поиска"
    await self.app.store.tg_api.send_keyboard(chat_id, SEARCHING_BUTTONS, "⏳ Ищем соперников...")


@router.message(BotCommands.cancel_search, BotButtons.cancel_search)
@ratelimit(seconds=3, scope="user")
async def handle_cancel_search(self, chat_id: int, user_id: int):
    """Выйти из очереди."""
    from app.store.tg_api.builders import PRIVATE_MENU_BUTTONS

    entry = await self.app.store.matchmaking.is_in_queue(user_id)
    if not entry:
        await self.app.store.tg_api.send_message(chat_id, "❌ Вы не в очереди поиска.")
        return

    await self.app.store.matchmaking.remove_from_queue(user_id)
    await self.app.store.tg_api.send_keyboard(
        chat_id, PRIVATE_MENU_BUTTONS, "✅ Поиск отменён."
    )