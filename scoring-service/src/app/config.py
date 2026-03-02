import os
from typing import Any

import yaml
from pydantic import BaseModel
from pydantic_settings import BaseSettings

SERVICE_NAME = os.getenv('SERVICE_NAME', 'scoring-service')
STUDENT = os.getenv('STUDENT_NAME', 'aabalymov')

def set_config(config_name: str) -> Any:
    if os.getenv('CONFIG_PATH') is None:
        config_path = 'config.yaml'
    else:
        config_path = str(os.getenv('CONFIG_PATH'))
    with open(config_path) as file:
        return yaml.safe_load(file)[config_name]

class Config(BaseSettings):
    """Конфиг приложения."""

    kafka_timeout_ms: int = 1000

    @property
    def kafka_url(self) -> Any:
        """Возвращает url Кафки."""
        return set_config('kafka')['bootstrap_servers']

    @property
    def kafka_topic(self) -> Any:
        return set_config('kafka')['topic']

class KafkaConfig(BaseModel):
    """Конфиг Кафки."""

    url: str
    request_timeout_ms: int
    topic: str
