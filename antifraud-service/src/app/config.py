import os
from typing import Any

import yaml


def set_config(config_name: str) -> Any:
    config_path = os.getenv('CONFIG_PATH', 'config.yaml')

    with open(config_path) as file:
        return yaml.safe_load(file)[config_name]

SERVICE_NAME = os.getenv('SERVICE_NAME', 'antifraud-service')
STUDENT = os.getenv('STUDENT_NAME', 'aabalymov')
