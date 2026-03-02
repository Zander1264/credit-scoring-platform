import asyncio
import json
import logging
import traceback
from typing import Any

from aiokafka import AIOKafkaConsumer, ConsumerRecord
from aiokafka.errors import KafkaConnectionError, KafkaError
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.data_interaction import update_user_data
from app.api.schemas import (
    CombinedRequestSchema,
)
from app.config import KafkaConfig
from app.db.database import engine


class KafkaConsumer:
    """Кафка консьюмер."""

    def __init__(
        self,
        kafka_config: KafkaConfig,
    ):
        """Инициализировать клиент."""
        self._kafka_config = kafka_config
        self._consumer = AIOKafkaConsumer(
            self._kafka_config.topic,
            bootstrap_servers=kafka_config.url,
            enable_auto_commit=False,
        )
        self._retry_timeout = kafka_config.retry_timeout_ms / 1000
        self._consume_task: asyncio.Task[Any] | None = None

    async def start(self) -> None:
        """Запускает консьюмер и подключается к Кафке."""
        await self._start()
        self._is_running = True
        if not await self.is_connected():
            self.reconnect_task = asyncio.create_task(self._reconnect())

    async def stop(self) -> None:
        """Останавливает консьюмер."""
        await self._consumer.stop()
        self._is_running = False
        if self._consume_task:
            self._consume_task.cancel()

    async def consume(self) -> None:
        """Читает сообщения из очереди."""
        while self._is_running:
            try:
                await self._consume()
            except KafkaError:
                logging.exception("Can't read message")
                await asyncio.sleep(self._retry_timeout)
            else:
                await self._commit_offset()

    async def is_connected(self) -> bool:
        """Проверяет доступность кафки."""
        try:
            await self._consumer._client.fetch_all_metadata()
        except KafkaError:
            logging.exception('Kafka is not available')
        else:
            return True
        return False

    async def _consume(self) -> None:
        """Читает сообщения из очереди."""
        async for message in self._consumer:
            await self._process_message(message)

    async def _process_message(self, message: ConsumerRecord) -> None:
        """Обрабатывает сообщения."""
        try:
            message_data = json.loads(message.value)
        except json.JSONDecodeError:
            logging.exception('Failed to process message')
            return

        version = message_data.get('version')
        if version != 1:
            logging.error(f'Unknown version: {version}')
            await self._commit_offset()
            return

        logging.info(
            ' '.join((
                'Received message:',
                f'topic: {message.topic},',
                f'partition: {message.partition},',
                f'offset: {message.offset},',
                f'key: {message.key},',
                f'value: {message_data},',
                f'timestamp: {message.timestamp}',
            )),
        )

        loan_id = message_data['history_entry']['loan_id']

        # Проверка дубликатов (идемпотентность)
        if self._is_loan_exists(loan_id):
            logging.warning(f'Loan {loan_id} already exists. Skipping...')
            await self._commit_offset()
            return

        event_type = message_data['event']
        if event_type == 'pioneer_accepted':
            await self._handle_pioneer(message_data)
        elif event_type == 'repeater_accepted':
            await self._handle_repeater(message_data)
        else:
            logging.error(f'Unknown event type: {event_type}')
            return

        await self._commit_offset()

    async def _commit_offset(self) -> None:
        """Записывает оффсет при успешной обработке сообщения."""
        await self._consumer.commit()

    async def _start(self) -> None:
        """Запускает консьюмер."""
        try:
            await self._consumer.start()
        except KafkaConnectionError:
            logging.error("Can't setup connection to Kafka")
        else:
            await self._start_consuming()

    async def _start_consuming(self) -> None:
        """Запускает чтение сообщений."""
        if self._consume_task:
            self._consume_task.cancel()
            self._consume_task = None
        self._consume_task = asyncio.create_task(self.consume())

    async def _reconnect(self) -> None:
        """Пытается переподключиться к Кафке."""
        is_connected = False
        while not is_connected:
            await asyncio.sleep(1)
            await self._start()
            is_connected = await self.is_connected()
        logging.info('Reconnected to Kafka')

    def _is_loan_exists(self, loan_id: str) -> bool:
        try:
            with open('src/app/repeater_list.json') as f:
                data = json.load(f)
                for client in data['clients']:
                    for loan in client['history']:
                        if loan['loan_id'] == loan_id:
                            return True
        except Exception as e:
            logging.error(f'Error checking loan existence: {e}')
        return False

    async def _handle_pioneer(self, message_data: dict[str, Any]) -> None:
        """
        Метод для обработки события 'pioneer_accepted',
        которое обновляет профиль клиента и добавляет кредитную запись.
        """
        # Извлекаем необходимые данные из сообщения
        logging.info('Handle pioneer start')
        phone = message_data['phone']
        profile:dict[str,str|int|bool] = message_data['profile']
        history_entry:dict[str,str|int|None] = message_data['history_entry']
        # Готовим запрос к FastAPI-сервису
        try:
            request_schema = CombinedRequestSchema(phone=phone,
                                               profile=profile,
                                               loan_entry=history_entry)
        except Exception as exc:
            logging.error(f'Error creating request schema: {exc}')
            raise
        try:
            async with AsyncSession(engine) as session:
                response = await update_user_data(request_schema, session=session)
        except Exception as exc:
            logging.error(f'Error updating user data: {exc}')
            logging.debug(traceback.format_exc())

        # Анализируем ответ
        if response.status_code == 200:
            logging.info(f'Data updated successfully for user {phone}.')
        elif response.status_code == 404:
            logging.error(f'User with phone {phone} was not found!')
        elif response.status_code == 409:
            logging.error(f'Duplicate loan entry detected for'
                          f'loan ID {history_entry['loan_id']}!')
        else:
            logging.error(f'Unexpected error during updating user data.'
                          f'Status code: {response.status_code},'
                          f'Message: {response.text}')

    async def _handle_repeater(self, message_data: dict[str, Any]) -> None:
        """
        Метод для обработки события 'repeater_accepted',
        которое добавляет кредитную запись.
        """
        # Извлекаем необходимые данные из сообщения
        phone = message_data['phone']
        history_entry:dict[str,str|int|None] = message_data['history_entry']

        # Готовим запрос к FastAPI-сервису
        try:
            request_schema = CombinedRequestSchema(phone=phone,
                                                   loan_entry=history_entry)
        except Exception as exc:
            logging.error(f'Error creating request schema: {exc}')
            raise

        try:
            async with AsyncSession(engine) as session:
                response = await update_user_data(request_schema, session=session)
        except Exception as exc:
            logging.error(f'Error updating user data: {exc}')
            logging.debug(traceback.format_exc())


        # Анализируем ответ
        if response.status_code == 200:
            logging.info(f'Data updated successfully for user {phone}.')
        elif response.status_code == 404:
            logging.error(f'User with phone {phone} was not found!')
        elif response.status_code == 409:
            logging.error(f'Duplicate loan entry detected for'
                          f'loan ID {history_entry['loan_id']}!')
        else:
            logging.error(f'Unexpected error during updating user data.'
                          f'Status code: {response.status_code},'
                          f'Message: {response.text}')
