import asyncio
import functools


def ratelimit(seconds: float, scope: str = "user_chat"):
    """
    Антиспам-декоратор.

    scope:
      "user_chat" — лимит на (user_id, chat_id, func).
                    Пользователь может нажать в разных чатах независимо.
                    Разные пользователи в одном чате не мешают друг другу.
                    Использовать для большинства команд и кнопок.

      "chat"      — лимит на (chat_id, func).
                    Любой пользователь в чате триггерит общий кулдаун.
                    Использовать для действий, меняющих состояние чата
                    (вступить в лобби, запустить игру).

      "user"      — лимит на (user_id, func) без привязки к чату.
                    Использовать для личных команд (статистика, правила, меню).
    """
    def decorator(func):
        @functools.wraps(func)
        async def wrapper(self, *args, **kwargs):
            app = getattr(self, "app", None)
            if app is None:
                return await func(self, *args, **kwargs)

            chat_id = kwargs.get("chat_id") or (args[0] if len(args) > 0 else None)
            user_id = kwargs.get("user_id") or (
                args[3] if len(args) > 3 
                else args[1] if len(args) > 1 
                else None
            )

            if scope == "user_chat":
                limit_key = f"rl:uc:{user_id}:{chat_id}:{func.__name__}"
                warn_key  = f"rl:uc:w:{user_id}:{chat_id}:{func.__name__}"
            elif scope == "chat":
                limit_key = f"rl:c:{chat_id}:{func.__name__}"
                warn_key  = f"rl:c:w:{chat_id}:{func.__name__}"
            else:
                limit_key = f"rl:u:{user_id}:{func.__name__}"
                warn_key  = f"rl:u:w:{user_id}:{func.__name__}"

            allowed = await app.store.redis.set_limit(limit_key, seconds)

            if not allowed:
                should_warn = await app.store.redis.set_limit(warn_key, 5)
                if should_warn:
                    asyncio.create_task(
                        app.store.tg_api.send_message(
                            chat_id,
                            f"⚠️ <b>Тише-тише!</b> Эта команда доступна раз в {int(seconds)} сек.",
                        )
                    )
                return

            return await func(self, *args, **kwargs)

        return wrapper
    return decorator