import asyncio
import functools
import time

from app.web import logger

def ratelimit(seconds: float):
    def decorator(func):
        @functools.wraps(func)
        async def wrapper(self, *args, **kwargs):
            app = getattr(self, "app", None)
            if app is None:
                return await func(self, *args, **kwargs)

            user_id = kwargs.get("user_id") or (args[1] if len(args) > 1 else None)
            chat_id = kwargs.get("chat_id") or (args[0] if len(args) > 0 else None)

            if user_id and app:
                if "ratelimit_cache" not in app:
                    app["ratelimit_cache"] = {}
                
                if "warned_users" not in app:
                    app["warned_users"] = {}

                now = time.time()
                last_time = app["ratelimit_cache"].get(user_id, 0)
                last_warn_time = app["warned_users"].get(user_id, 0)

                if now - last_time < seconds:
                    if now - last_warn_time > 5:
                        app["warned_users"][user_id] = now
                        if chat_id:
                            asyncio.create_task(
                                self.app.store.tg_api.send_message(
                                    chat_id, 
                                    f"⚠️ <b>Тише-тише!</b> Подождите {round(int(seconds) - (now - last_time))} сек. перед следующей командой."
                                )
                            )
                    return

                app["ratelimit_cache"][user_id] = now

            return await func(self, *args, **kwargs)
        return wrapper
    return decorator