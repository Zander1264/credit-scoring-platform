import os
from typing import Any

import yaml


def set_config(config_name: str) -> Any:
    if os.getenv('CONFIG_PATH') is None:
        config_path = 'config.yaml'
    else:
        config_path = str(os.getenv('CONFIG_PATH'))

    with open(config_path) as file:
        return yaml.safe_load(file)[config_name]

SERVICE_NAME = os.getenv('SERVICE_NAME', 'flow-selection-service')
STUDENT = os.getenv('STUDENT_NAME', 'aabalymov')
