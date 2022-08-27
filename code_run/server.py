import asyncio
import json
import logging
from typing import AsyncIterator, Callable, Type, Coroutine, Any

from aio_pika import Message
from aio_pika.abc import (
    AbstractChannel,
    ExchangeType,
    AbstractQueue,
    AbstractIncomingMessage,
)

from code_run.models import RunCodeTask, RunResult

RunCallback = Callable[[RunCodeTask], Coroutine[Any, Any, RunResult]]


class AmqpServer:
    def __init__(
        self,
        channel: AbstractChannel,
        queue_name: str,
        exchange_name: str,
    ):
        self.channel = channel
        self.queue_name = queue_name
        self.exchange_name = exchange_name
        self.queue: AbstractQueue | None = None
        self.tasks: set[asyncio.Task] = set()

    @classmethod
    async def from_channel(
        cls: Type["AmqpServer"],
        channel: AbstractChannel,
        queue_name: str,
        exchange_name: str,
    ):
        return await cls(channel, queue_name, exchange_name)._init()

    async def _init(self) -> "AmqpServer":
        logging.info("Begin init AmqpServer")
        self.queue = await self.channel.declare_queue(
            self.queue_name,
            durable=True,
            auto_delete=False,
        )

        logging.info(f"Declared queue {self.queue_name}")

        exchange = await self.channel.declare_exchange(
            self.exchange_name,
            type=ExchangeType.DIRECT,
        )

        logging.info(f"Declared exchange {self.exchange_name}")

        await self.queue.bind(exchange)

        logging.info(f'Bind "{self.queue_name}" -> "{self.exchange_name}" ')

        return self

    def __aiter__(self):
        return self.iterator().__aiter__()

    async def consume(self, callback: RunCallback) -> None:

        async for task_data in self.iterator():

            async def helper():
                try:
                    result = await callback(task_data)
                except Exception as e:
                    print(e)
                    raise e
                print(result)
                await self.send_result_message(result)

            task = asyncio.create_task(helper())
            task.add_done_callback(self.tasks.remove)
            self.tasks.add(task)

    async def iterator(self) -> AsyncIterator[RunCodeTask]:
        if self.queue is None:
            raise RuntimeError(
                "AmqpTaskProvider is not initialized await on it or call init() method"
            )

        async for message in self.queue.iterator():
            message: AbstractIncomingMessage
            try:
                parsed_message = self.parse_message(message)
                await message.ack()
                yield parsed_message
            except ValueError:
                await message.reject(requeue=False)

    @staticmethod
    def parse_message(message: AbstractIncomingMessage) -> RunCodeTask:
        return RunCodeTask(
            **json.loads(message.body.decode()),
            correlation_id=message.correlation_id,
            reply_to=message.reply_to,
        )

    async def send_result_message(self, result: RunResult) -> None:
        body = result.json()
        await self.channel.default_exchange.publish(
            Message(
                body=body.encode(),
                correlation_id=result.correlation_id,
            ),
            routing_key=result.reply_to,
        )
