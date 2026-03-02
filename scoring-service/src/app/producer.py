import asyncio
import json
import logging

from aiokafka import AIOKafkaProducer
from aiokafka.errors import KafkaConnectionError, KafkaError

from app.config import KafkaConfig
from app.monitoring.tracing import get_tracer

tracer = get_tracer()

class KafkaProducer:
    def __init__(self, kafka_config:KafkaConfig =KafkaConfig) -> None:
        self._kafka_config = kafka_config
        self._producer = AIOKafkaProducer(
            bootstrap_servers=kafka_config.url,
            request_timeout_ms=kafka_config.request_timeout_ms,
        )
        self._topic = self._kafka_config.topic

    async def start(self) -> None:
        """Запускает продюсер и подключается к Кафке."""
        await self._start()
        if not await self.is_connected():
            self.reconnect_task = asyncio.create_task(self._reconnect())

    async def stop(self) -> None:
        """Останавливает продюсер."""
        try:
            await self._producer.flush()
            await self._producer.stop()
        except KafkaError:
            logging.exception('Error while stopping producer')
            raise
        finally:
            logging.info('Producer stopped')

    async def send(
        self,
        message: dict[str,str|int],
        key: str
    ) -> None:
        with tracer.start_as_current_span('kafka_send'):
            """Отправляет сообщение в топик.."""
            message_data = bytes(
                json.dumps(message, default=str),
                encoding='utf-8',
            )
            try:
                await self._producer.send_and_wait(
                    topic=self._topic,
                    value=message_data,
                    key=bytes(key, encoding='utf-8'),
                )
            except KafkaError:
                logging.exception("Can't send message to kafka")
                raise

            logging.info('Message sent to Kafka')

    async def is_connected(self) -> bool:
        try:
            await self._producer.client.fetch_all_metadata()
        except KafkaError:
            logging.exception('Kafna is not available')
        else:
            return True
        return False

    async def _start(self) -> None:
        try:
            await self._producer.start()
        except KafkaConnectionError:
            logging.error('Can`t connect to Kafka')

    async def _reconnect(self) -> None:
        attemts = 0
        max_attemts = 5
        delay = 1
        while attemts < max_attemts:
            await self._start()
            if await self.is_connected():
                logging.info('Reconnected to Kafka')
                return

            await asyncio.sleep(delay)
            delay *= 2
            attemts += 1
        logging.error('Failed to reconnect to Kafka after multiple attempts')
