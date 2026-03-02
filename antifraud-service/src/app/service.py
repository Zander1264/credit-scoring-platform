import argparse
import logging
import os
from pathlib import Path

import uvicorn
from fastapi import FastAPI

from app.api import main_router
from app.config import set_config


def check_log_files_and_folders(project_name: str, module_name: str) -> str:
    root_dir = Path.cwd().parent
    log_dir = root_dir / 'logs'
    project_log_dir = log_dir / project_name
    log_file_name = f'{module_name}.log'
    full_log_path = project_log_dir / log_file_name

    project_log_dir.mkdir(parents=True, exist_ok=True)

    return str(full_log_path)

def create_app() -> FastAPI:
    app = FastAPI(
        title='Antifraud Service',
        openapi_url='/openapi.json'
    )
    app.include_router(main_router)

    return app

if __name__ == '__main__':
    log_file_path = check_log_files_and_folders('flow-selection-service', __name__)
    file_handler = logging.FileHandler(log_file_path)
    console_handler = logging.StreamHandler()
    logging.basicConfig(
        level=logging.INFO,
        format='[%(asctime)s - %(levelname)s] %(name)s: %(message)s',
        handlers=[file_handler, console_handler],
    )

    logger = logging.getLogger(__name__)
    logger.propagate = True

    parser = argparse.ArgumentParser(description='Flow Selection Service')
    parser.add_argument('--config', default='config.yaml')
    args = parser.parse_args()
    os.environ['CONFIG_PATH'] = args.config

    config = set_config('app')
    app = create_app()

    uvicorn.run(
        app,
        host=config['host'],
        port=config['port'],
        log_config=None
    )
