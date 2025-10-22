# server/consumer/consumer.py
# Модуль для получения данных из очереди RabbitMQ и перенаправления их в дочерние модули

import asyncio
import json
import aio_pika
from typing import Optional
from contextlib import suppress

from server.rabbitmq.validation import validate_message
from server.modules.write_to_database import Writer as DatabaseWriter
from server.modules.write_to_console import Writer as ConsoleWriter
from server.modules.write_to_files import Writer as FilesWriter
from server.config.schema import ServerConfig
from server.config.config import ConfigManager as cfg


class RabbitMQConsumer:
    def __init__(self):
        """ Функция для инициализации модуля
        """
        
        self.config: ServerConfig = cfg.config                                  # Конфигурация всего проекта
        
        self.connection: Optional[aio_pika.RobustConnection] = None             # Соединение с RabbitMQ
        self.channel: Optional[aio_pika.RobustChannel] = None                   # Канал для работы с RabbitMQ
        self.queue: Optional[aio_pika.RobustQueue] = None                       # Очередь для получения сообщений
        self.service_queue: Optional[aio_pika.RobustQueue] = None               # Очередь для получения сообщений (сервисных)
        self.consumer_tag: Optional[str] = None                                 # Тег для получения сообщений
        self.service_tag: Optional[str] = None                                  # Тег для получения сообщений (сервисных)
        self._running = False                                                   # Статус работы модуля
        self._restart_requested = False                                         # Статус необходимости перезапуска модуля
        self._lock = asyncio.Lock()                                             # Блокировка для thread-safe операций

        self._console_client: Optional[ConsoleWriter] = None                    # Клиент для вывода логов в консоль
        self._database_client: Optional[DatabaseWriter] = None                  # Клиент для сохранения логов в БД
        self._files_client: Optional[FilesWriter] = None                        # Клиент для сохранения логов в файлы

    async def _init_clients(self) -> bool:
        """ Инициализация клиентов

        Returns:
            bool -- Статус инициализации
        """

        try:
            # Закрываем старые клиенты
            if self._files_client:
                await self._files_client.close_all()

            # Создаём новые
            if self.config.console.enabled:
                self._console_client = ConsoleWriter(cfg.config.console)
            else:
                self._console_client = None

            if self.config.timescaledb.enabled:
                self._database_client = DatabaseWriter(self.config.timescaledb)
            else:
                self._database_client = None

            if self.config.files.enabled:
                self._files_client = FilesWriter(self.config.files)
            else:
                self._files_client = None
                
            return True
        except Exception as e:
            print("Error initializing clients:", e)
            return False

    async def _distribution_message(self, message: aio_pika.IncomingMessage):
        """ Функция для обработки сообщений из очереди

        Arguments:
            message {aio_pika.IncomingMessage} -- Сообщение из очереди
        """
        
        async with message.process():
            try:
                dict_message: dict = json.loads(message.body.decode())
                result_validation = await validate_message(dict_message)
                if not result_validation:
                    print("⚠️ Некорректные данные в сообщении, пропускаем.")
                    return

                if self.config.timescaledb.enabled and self._database_client:
                    await self._database_client.write_log(log=dict_message)

                if self.config.console.enabled and self._console_client:
                    await self._console_client.print_log(dict_message)

                if self.config.files.enabled and self._files_client:
                    await self._files_client.write_log(dict_message)

            except json.JSONDecodeError:
                print(f"⚠️ Ошибка декодирования JSON: {message.body.decode()[:100]}...")
            except Exception as e:
                print(f"Ошибка обработки сообщения: {e}")

    async def _distribution_service_message(self, message: aio_pika.IncomingMessage):
        """ Функция для обработки сервисных сообщений

        Arguments:
            message {aio_pika.IncomingMessage} -- Сообщение из очереди
        """
        
        async with message.process():
            try:
                dict_message: dict = json.loads(message.body.decode())
                if dict_message.get("code") == 100 or dict_message.get("detail") == "Update config":
                    print("🔄 Получен сигнал обновления конфигурации. Запрашиваем перезапуск...")
                    self._restart_requested = True
                    # Прерываем основной цикл
                    self._running = False
            except Exception as e:
                print(f"Error processing service message: {e}")

    async def _connect(self) -> bool:
        """ Функция для подключения к RabbitMQ

        Returns:
            bool -- Статус подключения
        """
        
        try:
            config = self.config.rabbitmq
            url = f"amqp://{config.username}:{config.password}@{config.host}:{config.port}/"
            
            self.connection = await aio_pika.connect_robust(url) # type: ignore
            self.channel = await self.connection.channel() # type: ignore
            self.queue = await self.channel.declare_queue( # type: ignore
                config.queue,
                durable=True,
                auto_delete=False,
                arguments={"x-message-ttl": 30000}
            )
            self.service_queue = await self.channel.declare_queue( # type: ignore
                "service_queue",
                durable=True,
                auto_delete=False,
                arguments={"x-message-ttl": 30000}
            )

            self.consumer_tag = await self.queue.consume(self._distribution_message) # type: ignore
            self.service_tag = await self.service_queue.consume(self._distribution_service_message) # type: ignore
            
            return True
        except Exception as e:
            print("Error connecting to RabbitMQ:", e)
            return False

    async def start(self) -> bool:
        """ Функция для запуска модуля

        Raises:
            e: Ошибка запуска модуля

        Returns:
            bool -- Статус запуска модуля
        """
        
        try:
            await self._init_clients()
            await self._connect()
            self._running = True
            self._restart_requested = False
            
            return True
        except Exception as e:
            print("Error in start consumer:", e)
            self._running = False
            raise e

    async def stop(self) -> bool:
        try:
            if self.consumer_tag and self.queue:
                with suppress(Exception):
                    await self.queue.cancel(self.consumer_tag)
                    
            if self.service_tag and self.service_queue:
                with suppress(Exception):
                    await self.service_queue.cancel(self.service_tag)
                    
            if self.channel:
                with suppress(Exception):
                    await self.channel.close()
                    
            if self.connection:
                with suppress(Exception):
                    await self.connection.close()
                    
            if self._files_client:
                with suppress(Exception):
                    await self._files_client.close_all()
            self._running = False
            print("Consumer stop.")
            
            return True
        except Exception as e:
            print("Error in stop consumer:", e)
            return False

    async def restart(self) -> bool:
        """ Функция для перезапуска модуля

        Returns:
            bool -- Статус перезапуска модуля
        """
        
        try:
            print("Update config...")
            await self.stop()
            self.config = cfg.config
            await self.start()
            print("Update config complete.")
            
            return True
        except Exception as e:
            print("Error in update config:", e)
            return False

    async def run_forever(self) -> None:
        """ Функция для запуска цикла обработки сообщений
        """
        
        await self.start()
        try:
            while True:
                # Запускаем основной цикл
                while self._running:
                    await asyncio.sleep(1)
                
                # Проверка на требование перезапуска
                if self._restart_requested:
                    await self.restart()
                else:
                    break
        except asyncio.CancelledError:
            print("   -> Задача Consumer отменена.")
        finally:
            if not self._restart_requested:
                await self.stop()
                
                
if __name__ == "__main__":
    consumer = RabbitMQConsumer()
    asyncio.run(consumer.run_forever())
    