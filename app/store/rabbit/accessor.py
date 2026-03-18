import asyncio
import json
import logging
import typing

import aio_pika

if typing.TYPE_CHECKING:
    from app.web.app import Application

QUEUE_NAME = "tg_updates"


class RabbitAccessor:
    def __init__(self, app: "Application"):
        self.app = app
        self._connection = None
        self._channel = None
        self._queue = None
        self._consumer_task = None

    async def connect(self) -> None:
        cfg = self.app.config.rabbit
        url = f"amqp://{cfg.user}:{cfg.password}@{cfg.host}:{cfg.port}/"
        self._connection = await aio_pika.connect_robust(url)
        self._channel = await self._connection.channel()
        await self._channel.set_qos(prefetch_count=1)
        self._queue = await self._channel.declare_queue(QUEUE_NAME, durable=True)
        logging.info("RabbitMQ connected")

    async def disconnect(self) -> None:
        if self._consumer_task:
            self._consumer_task.cancel()
            await asyncio.gather(self._consumer_task, return_exceptions=True)
        if self._connection and not self._connection.is_closed:
            await self._connection.close()
        logging.info("RabbitMQ disconnected")

    async def publish(self, update: dict) -> None:
        """Положить апдейт в очередь. Вызывается из Poller вместо handle_update."""
        await self._channel.default_exchange.publish(
            aio_pika.Message(
                body=json.dumps(update).encode(),
                delivery_mode=aio_pika.DeliveryMode.PERSISTENT,
            ),
            routing_key=QUEUE_NAME,
        )

    async def start_consuming(self, handle_update) -> None:
        """Запустить потребителя очереди в фоновом таске."""
        self._consumer_task = asyncio.create_task(
            self._consume(handle_update)
        )

    async def _consume(self, handle_update) -> None:
        try:
            async with self._queue.iterator() as queue_iter:
                async for message in queue_iter:
                    # requeue=False — не возвращать в очередь при ошибке,
                    # иначе битое сообщение будет обрабатываться бесконечно
                    async with message.process(requeue=False):
                        try:
                            update = json.loads(message.body.decode())
                            await handle_update(update)
                        except Exception as e:
                            logging.error(
                                f"Error processing update from RabbitMQ: {e}",
                                exc_info=True,
                            )
        except asyncio.CancelledError:
            logging.info("RabbitMQ consumer stopped")
        except Exception as e:
            logging.error(f"RabbitMQ consumer crashed: {e}", exc_info=True)
 