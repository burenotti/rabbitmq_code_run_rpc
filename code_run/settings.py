from pydantic import BaseSettings, AmqpDsn, BaseModel
from runbox.models import Limits


class VersionConfig(BaseModel):
    command: str | list[str]
    image: str


class LangConfig(BaseModel):
    file_name: str
    versions: dict[str, VersionConfig]


class Settings(BaseSettings):
    amqp: AmqpDsn
    limits: Limits
    languages: dict[str, LangConfig]


settings = Settings.parse_file("./settings.json")
