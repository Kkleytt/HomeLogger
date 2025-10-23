# server/consumer/consumer.py
# Модуль для получения данных из очереди RabbitMQ и перенаправления их в дочерние модули

import asyncio
import json
import logging
import aio_pika
from typing import Optional
from contextlib import suppress

from server.rabbitmq.validation import validate_message
from server.modules.write_to_database import Writer as DatabaseWriter
from server.modules.write_to_console import Writer as ConsoleWriter
from server.modules.write_to_files import Writer as FilesWriter
from server.config.schema import ServerConfig
from server.config.config import ConfigManager as cfg 
from server.config.logging import setup_logging

# Импортируем исключения
from server.rabbitmq.errors import ExceptionRabbitMQ as Exc

# --- Настройка логгера ---
setup_logging()
logger = logging.getLogger(__name__)

class RabbitMQConsumer:
    def __init__(self):
        """ Функция для инициализации модуля
        """
        # self.config: ServerConfig = cfg.config  # Теперь получаем из config_manager
        self.config: ServerConfig = cfg.config # Используем глобальный config_manager
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

    def _log_and_raise(self, exc_class, message: str, original_exc: Exception):
        """
        Централизованная функция для логирования и поднятия исключения.

        Args:
            exc_class: Класс исключения (например, Exc.StartError).
            message: Сообщение для лога и нового исключения.
            original_exc: Исключение, которое стало причиной (для цепочки исключений).
        """
        
        log_message = f"{exc_class.__name__}: {message}"
        if original_exc:
            logger.error(log_message, exc_info=True)
            raise exc_class(message) from original_exc
        else:
            logger.error(log_message)
            raise exc_class(message)

    async def _init_clients(self) -> None:
        """
        Инициализирует клиентов для записи логов.
        Бросает ModuleError при ошибках.
        """
        try:
            logger.debug("Инициализация клиентов...")
            # Закрываем старые клиенты (если они есть)
            if self._files_client:
                try:
                    await self._files_client.close_all()
                    logger.debug("Старый FilesClient закрыт.")
                except Exception as e:
                    logger.warning(f"Предупреждение при закрытии старого FilesClient: {e}")

            # Создаём новые клиенты на основе текущей конфигурации
            if self.config.console.enabled:
                logger.debug("Создание ConsoleClient...")
                self._console_client = ConsoleWriter(self.config.console)
            else:
                logger.debug("Консоль отключена, ConsoleClient не создаётся.")
                self._console_client = None

            if self.config.timescaledb.enabled:
                logger.debug("Создание DatabaseClient...")
                self._database_client = DatabaseWriter(self.config.timescaledb)
            else:
                logger.debug("TimescaleDB отключена, DatabaseClient не создаётся.")
                self._database_client = None

            if self.config.files.enabled:
                logger.debug("Создание FilesClient...")
                self._files_client = FilesWriter(self.config.files)
            else:
                logger.debug("Файловый вывод отключён, FilesClient не создаётся.")
                self._files_client = None

            logger.debug("Клиенты инициализированы успешно.")

        except Exception as e:
            self._log_and_raise(
                Exc.ModuleError,
                f"Ошибка инициализации клиентов: {e}",
                e
            )

    async def _distribution_message(self, message: aio_pika.IncomingMessage) -> None:
        """
        Логика обработки обычного сообщения.
        """
        async with message.process():
            try:
                dict_message: dict = json.loads(message.body.decode())
                result_validation = await validate_message(dict_message)
                if not result_validation:
                    logger.warning("Некорректные данные в сообщении, пропускаем.")
                    return

                # Запись в БД
                if self.config.timescaledb.enabled and self._database_client:
                    try:
                        await self._database_client.write_log(log=dict_message)
                    except Exception as e:
                        logger.error(f"Ошибка записи в БД: {e}")

                # Запись в консоль
                if self.config.console.enabled and self._console_client:
                    try:
                        await self._console_client.print_log(dict_message)
                    except Exception as e:
                        logger.error(f"Ошибка вывода в консоль: {e}")

                # Запись в файлы
                if self.config.files.enabled and self._files_client:
                    try:
                        await self._files_client.write_log(dict_message)
                    except Exception as e:
                        logger.error(f"Ошибка записи в файл: {e}")

            except json.JSONDecodeError as e:
                logger.error(f"Ошибка декодирования JSON в сообщении: {e}. Тело: {message.body.decode()[:100]}...")
            except Exception as e:
                logger.error(f"Неожиданная ошибка при обработке обычного сообщения: {e}", exc_info=True)

    async def _distribution_service_message(self, message: aio_pika.IncomingMessage) -> None:
        """
        Логика обработки сервисного сообщения.
        """
        async with message.process():
            try:
                dict_message: dict = json.loads(message.body.decode())
                # Проверяем на сигнал обновления конфигурации
                if dict_message.get("code") == 100 or dict_message.get("detail") == "Update config":
                    logger.info("Получен сигнал обновления конфигурации. Запрашиваем перезапуск...")
                    self._restart_requested = True
                    # Прерываем основной цикл run_forever
                    self._running = False
                    # Опционально: можно вызвать asyncio.current_task().cancel() или установить asyncio.Event
                    # для более быстрого реагирования, но простой флаг _running уже работает.

            except json.JSONDecodeError as e:
                logger.error(f"Ошибка декодирования JSON в сервисном сообщении: {e}. Тело: {message.body.decode()[:100]}...")
            except Exception as e:
                logger.error(f"Неожиданная ошибка при обработке сервисного сообщения: {e}", exc_info=True)

    async def _connect(self) -> None:
        """
        Подключается к RabbitMQ и объявляет очереди.
        Бросает ConnectionError или StartError при ошибках.
        """
        try:
            logger.debug("Подключение к RabbitMQ...")
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
                "service_queue", # Возможно, лучше вынести в конфиг
                durable=True,
                auto_delete=False,
                arguments={"x-message-ttl": 30000}
            )

            self.consumer_tag = await self.queue.consume(self._distribution_message) # type: ignore
            self.service_tag = await self.service_queue.consume(self._distribution_service_message) # type: ignore
            logger.info(f"Успешно подключено к RabbitMQ: {config.host}:{config.port}, queues: {config.queue}, service_queue")

        except (aio_pika.exceptions.AMQPConnectionError, OSError) as e: # Ловим конкретные ошибки подключения
            self._log_and_raise(
                Exc.ConnectionError,
                f"Ошибка подключения к RabbitMQ {self.config.rabbitmq.host}:{self.config.rabbitmq.port} - {e}",
                e
            )
        except Exception as e: # Ловим любые другие ошибки при подключении
            self._log_and_raise(
                Exc.StartError,
                f"Ошибка при объявлении очередей или подписке: {e}",
                e
            )

    async def start(self) -> None:
        """
        Запускает модуль: инициализирует клиентов, подключается к RabbitMQ.
        Бросает StartError при ошибках.
        """
        try:
            logger.info("Запуск Consumer...")
            await self._init_clients()
            await self._connect()
            self._running = True
            self._restart_requested = False
            logger.info("Consumer запущен успешно.")

        except (Exc.ModuleError, Exc.ConnectionError) as e: # Пробрасываем наши специфичные ошибки
            logger.error(f"Критическая ошибка при запуске Consumer: {e}")
            self._running = False
            raise # Пробрасываем дальше
        except Exception as e: # Ловим любые другие ошибки
            self._log_and_raise(
                Exc.StartError,
                f"Неизвестная ошибка при запуске Consumer: {e}",
                e
            )

    async def stop(self) -> None:
        """
        Останавливает модуль: отменяет подписки, закрывает каналы и соединения.
        Логирует ошибки, но не бросает исключения (для корректной остановки).
        """
        logger.info("Остановка Consumer...")
        try:
            if self.consumer_tag and self.queue:
                logger.debug("Отмена подписки на основную очередь...")
                with suppress(Exception): # Игнорируем ошибки при отмене (например, если соединение уже разорвано)
                    await self.queue.cancel(self.consumer_tag)
                self.consumer_tag = None

            if self.service_tag and self.service_queue:
                logger.debug("Отмена подписки на сервисную очередь...")
                with suppress(Exception):
                    await self.service_queue.cancel(self.service_tag)
                self.service_tag = None

            if self.channel:
                logger.debug("Закрытие канала...")
                with suppress(Exception):
                    await self.channel.close()
                self.channel = None

            if self.connection:
                logger.debug("Закрытие соединения...")
                with suppress(Exception):
                    await self.connection.close()
                self.connection = None

            if self._files_client:
                logger.debug("Закрытие FilesClient...")
                with suppress(Exception):
                    await self._files_client.close_all()
                self._files_client = None

            self._running = False
            logger.info("Consumer остановлен.")

        except Exception as e:
            logger.error(f"Ошибка при остановке Consumer: {e}", exc_info=True) # Логгируем traceback
            # Не поднимаем исключение, так как цель - остановка, а не ошибка

    async def restart(self) -> None:
        """
        Перезапускает модуль: останавливает, обновляет конфигурацию, запускает.
        Бросает ConfigUpdateError, StartError, StopError при ошибках.
        """
        try:
            logger.info("Начало перезапуска Consumer...")
            await self.stop()

            # Обновляем конфигурацию из config_manager
            logger.debug("Обновление конфигурации из config_manager...")
            try:
                self.config = cfg.config # Получаем актуальную конфигурацию
                logger.debug("Конфигурация обновлена из config_manager.")
            except AttributeError as e: # Если config_manager.config недоступен
                self._log_and_raise(
                    Exc.ConfigUpdateError,
                    f"Ошибка доступа к новой конфигурации: {e}",
                    e
                )

            await self.start()
            logger.info("Consumer успешно перезапущен.")

        except (Exc.StartError, Exc.StopError, Exc.ConfigUpdateError) as e: # Пробрасываем наши специфичные ошибки
            logger.error(f"Ошибка при перезапуске Consumer: {e}")
            raise # Пробрасываем дальше
        except Exception as e: # Ловим любые другие ошибки
            self._log_and_raise(
                Exc.ConfigUpdateError, # Или StartError, если ошибка в start
                f"Неизвестная ошибка при перезапуске Consumer: {e}",
                e
            )

    async def run_forever(self) -> None:
        """
        Основной цикл работы Consumer.
        Бросает ModuleError при ошибках в start/stop/restart или непредвиденных ошибках.
        """
        try:
            await self.start()

            while True:
                # Основной цикл работы
                if self._running:
                    logger.info(f"Consumer запущен и слушает {self.config.rabbitmq.host}:{self.config.rabbitmq.port}")
                    while self._running:
                        await asyncio.sleep(1)

                # Проверка на требование перезапуска
                if self._restart_requested:
                    logger.info("Запрошено обновление конфигурации, начинаю перезапуск...")
                    await self.restart() # restart теперь бросает исключение при ошибке
                    # Если restart успешен, _running снова True, и цикл продолжается
                else:
                    # Если _restart_requested не True, выходим из внешнего while
                    break

        except asyncio.CancelledError:
            logger.info("Задача Consumer отменена.")
        except (Exc.StartError, Exc.StopError, Exc.ConfigUpdateError) as e:
            logger.error(f"Критическая ошибка в run_forever, завершение: {e}")
            # Пробрасываем ошибку дальше, если вызывающий код готов её обработать
            raise
        except Exception as e:
            self._log_and_raise(
                Exc.ModuleError,
                f"Неожиданная ошибка в run_forever: {e}",
                e
            )
        finally:
            # Всегда пытаемся остановиться, если не запрошен перезапуск
            if not self._restart_requested:
                await self.stop() # stop не бросает исключения


# --- Пример использования ---
if __name__ == "__main__":
    consumer = RabbitMQConsumer()
    
    try:
        asyncio.run(consumer.run_forever())
    except (Exc.StartError, Exc.StopError, Exc.ConfigUpdateError, Exc.ModuleError) as e:
        logger.critical(f"Критическая ошибка в Consumer, работа завершена: {e}")
    except KeyboardInterrupt:
        logger.info("Получен сигнал KeyboardInterrupt, завершение.")
    except Exception as e:
        logger.critical(f"Необработанная ошибка верхнего уровня: {e}", exc_info=True)
