import logging
import os
import re
import traceback
from typing import Any

import redis
from fastapi import HTTPException

from app.config import set_config

config = set_config('redis')

redis_url = str(os.getenv('REDIS_HOST'))
redis_port = os.getenv('REDIS_PORT', 6379)
redis_password: str|None = os.getenv('REDIS_PASSWORD', None)
key_prefix: str|None = os.getenv('KEY_PREFIX', None)

match_tcp = re.search(r'tcp://([^:]+):(\d+)', redis_url)
if match_tcp:
    redis_url = str(match_tcp.group(1))
    redis_port = str(match_tcp.group(2))

if redis_port is None:
    raise ValueError('No redis port')
else:
    redis_port = int(redis_port)

redis_timeout = config['timeout']
TTL = config['ttl']

if redis_password is None:
    redis_client = redis.Redis(host=redis_url,
                           port=redis_port,
                           decode_responses=True,
                           socket_timeout=redis_timeout)
else:
    redis_client = redis.Redis(host=redis_url,
                            port=redis_port,
                            password=redis_password,
                            decode_responses=True,
                            socket_timeout=redis_timeout)

def check_redis_connection(r: redis.Redis) -> bool:
    try:
        r.ping()
        logging.info('Redis connection successful')
        return True
    except redis.exceptions.ConnectionError as e:
        logging.warning(f'Redis connection failed: {e}')
        return False

async def get_cache(r: redis.Redis,
                    name:str) -> dict[str, Any]:
    if key_prefix is None:
        key = f'agify:{name.lower()}'
    else:
        key = f'{key_prefix}:{name.lower()}'
    try:
        cached:str = str(r.get(key))
        logging.info(f'Cache: {cached}')
        if cached:
            return {'name': name, 'cache': True,
                    'ttl': r.ttl(key), 'value': cached}
        return {'name': name, 'cache': False,
                'ttl': None, 'value': None}
    except redis.exceptions.RedisError as e:
        logging.error(f'Redis error: {e}')
        raise HTTPException(500, 'Redis error') from e
    except Exception as e:
        logging.error(f'Unexpected error: {e}')
        logging.debug(traceback.format_exc())
        raise HTTPException(500, 'Unexpected error') from e

async def set_cache(r: redis.Redis,
                    name: str,
                    value: int,
                    ttl: int = TTL) -> None:
    if key_prefix is None:
        key = f'agify:{name.lower()}'
    else:
        key = f'{key_prefix}:{name.lower()}'
    try:
        r.set(key, str(value), ex=ttl)
    except redis.exceptions.RedisError as e:
        logging.error(f'Redis error: {e}')
        raise HTTPException(500, 'Redis error') from e
    except Exception as e:
        logging.error(f'Unexpected error: {e}')
        logging.debug(traceback.format_exc())
        raise HTTPException(500, 'Unexpected error') from e
