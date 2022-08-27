import asyncio
import logging
from uuid import uuid4

from aio_pika.abc import (
    AbstractChannel,
    AbstractExchange,
    AbstractQueue,
    AbstractIncomingMessage,
)

from code_run.models import RunCodeTask, RunResult


class RunboxClient:
    def __init__(
        self,
        channel: AbstractChannel,
        callback_queue: AbstractQueue,
        routing_key: str,
        custom_exchange: AbstractExchange | None = None,
    ) -> None:
        self.routing_key = routing_key
        self.channel = channel
        self._custom_exchange: AbstractExchange = custom_exchange
        self._callback_queue: AbstractQueue = callback_queue
        self._consumer_tag: str | None = None
        self._futures: dict[str, asyncio.Future] = {}

    @property
    def exchange(self) -> AbstractExchange:
        return (
            self._custom_exchange
            if self._custom_exchange
            else self.channel.default_exchange
        )

    @classmethod
    async def from_channel(
        cls,
        channel: AbstractChannel,
        routing_key: str,
        custom_exchange: AbstractExchange | None = None,
    ) -> "RunboxClient":

        queue = await channel.declare_queue(
            routing_key,
            durable=True,
        )

        if custom_exchange:
            await queue.bind(custom_exchange)

        callback_queue = await channel.declare_queue(
            auto_delete=True,
            exclusive=True,
        )

        client = RunboxClient(
            channel=channel,
            callback_queue=callback_queue,
            routing_key=routing_key,
            custom_exchange=custom_exchange,
        )

        client._consumer_tag = await callback_queue.consume(
            callback=client._process_result,
            exclusive=True,
            no_ack=False,
        )

        return client

    async def run(
        self, code: str, language: str, version: str, stdin: str = ""
    ) -> RunResult:
        correlation_id = str(uuid4())
        message = RunCodeTask(
            stdin=stdin,
            code=code,
            language=language,
            language_version=version,
            reply_to=self._callback_queue.name,
            correlation_id=correlation_id,
        ).to_message()

        await self.exchange.publish(
            message,
            routing_key=self.routing_key,
        )

        future = asyncio.Future()
        self._futures[correlation_id] = future
        return await future

    async def _process_result(self, message: AbstractIncomingMessage) -> None:
        if future := self._futures.get(message.correlation_id):
            try:
                result = RunResult.from_message(message)
                await message.ack()
                future.set_result(result)
            except Exception as error:
                future.set_exception(error)
            finally:
                del self._futures[message.correlation_id]
        else:
            logging.warning(
                f"rejecting message with unexpected "
                f"correlation_id {message.correlation_id}"
            )
            await message.reject(requeue=False)

    async def close(self) -> None:
        await self._callback_queue.delete(if_unused=False, if_empty=False)
