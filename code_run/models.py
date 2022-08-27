from typing import TypeVar, Type

from aio_pika import Message
from aio_pika.abc import AbstractIncomingMessage
from pydantic import BaseModel, Field

Model = TypeVar("Model", bound="RabbitmqMixin")


class RabbitmqMixin(BaseModel):
    correlation_id: str | None = Field(None, exclude=True)
    reply_to: str | None = Field(None, exclude=True)

    def to_message(self: Model) -> Message:
        exclude = {"correlation_id", "reply_to"}
        return Message(
            correlation_id=self.correlation_id,
            reply_to=self.reply_to,
            body=self.json(exclude=exclude).encode(),
        )

    @classmethod
    def from_message(
        cls: Type[Model], message: AbstractIncomingMessage, encoding: str = "utf-8"
    ) -> Model:
        model = cls.parse_raw(message.body, encoding=encoding)
        model.reply_to = message.reply_to
        model.correlation_id = message.correlation_id
        return model


class RunCodeTask(RabbitmqMixin):
    stdin: str = ""
    code: str
    language: str
    language_version: str


class RunResult(RabbitmqMixin):
    ok: bool
    execution_time: float
    logs: list[str]

    time_limit: bool = False
    memory_limit: bool = False
    runtime_error: bool = False
