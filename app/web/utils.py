import asyncio
import functools
import time

def ratelimit(seconds: float):
    def decorator(func):
        @functools.wraps(func)
        async def wrapper(self, *args, **kwargs):
            app = getattr(self, "app", None)
            if app is None:
                return await func(self, *args, **kwargs)

            user_id = kwargs.get("user_id") or (args[1] if len(args) > 1 else None)
            chat_id = kwargs.get("chat_id") or (args[0] if len(args) > 0 else None)

            limit_key = f"rl:{user_id}:{func.__name__}"

            warn_key = f"rl_warn:{user_id}:{func.__name__}"

            allowed = await self.app.store.redis.set_limit(limit_key, seconds)

            if not allowed:
                should_warn = await self.app.store.redis.set_limit(warn_key, 5)

                if should_warn:
                    asyncio.create_task(
                                    self.app.store.tg_api.send_message(
                                        chat_id, 
                                        f"⚠️ <b>Тише-тише!</b> Команда доступна раз в {seconds} секунд. Подождите немного!"
                                    ))
                return
            return await func(self, *args, **kwargs)
        return wrapper
    return decorator