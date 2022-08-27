from pydantic import BaseSettings, AmqpDsn, BaseModel
from runbox.models import Limits


class VersionConfig(BaseModel):
    command: str | list[str]
    image: str


class LangConfig(BaseModel):
    file_name: str
    versions: dict[str, VersionConfig]


class Settings(BaseSettings):
    code_run_exchange: str
    code_run_queue: str
    amqp: AmqpDsn
    limits: Limits
    languages: dict[str, LangConfig]


settings = Settings.parse_file("./settings.json")
