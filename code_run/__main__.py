import asyncio
import functools
import logging

import aio_pika
from runbox import DockerExecutor

from executor import execute
from settings import settings
from .server import AmqpServer


async def main():
    logging.basicConfig(
        level=logging.INFO, format="%(asctime)s %(levelname)s: %(message)s"
    )
    conn = await aio_pika.connect_robust(settings.amqp)
    async with conn:
        async with conn.channel() as chan:
            executor = DockerExecutor()
            server = await AmqpServer.from_channel(
                chan, settings.code_run_queue, settings.code_run_exchange
            )
            consumer = functools.partial(execute, executor=executor)
            await server.consume(consumer)
            await executor.close()
            await server.close()


asyncio.run(main())
