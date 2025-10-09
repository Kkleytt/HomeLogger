# app/src/lib/logger.py
# Библиотека для логирования сообщений в RabbitMQ

import inspect
from typing import Optional, Literal
from pydantic import BaseModel, Field
from contextvars import ContextVar
from datetime import datetime, timezone
from zoneinfo import ZoneInfo
import asyncio
import aio_pika
import json


# Класс для валидации конфигурации
class LoggerConfig(BaseModel):
    # Обязательные поля
    host: str
    port: int
    username: str
    password: str
    queue: str
    project_name: str
    
    # Необязательные поля
    console_enable: bool = True
    console_time_format: str = "%Y-%m-%d %H:%M:%S"
    console_time_zone: ZoneInfo = Field(default_factory=lambda: ZoneInfo("Europe/London"))

    class Config:
        extra = "forbid"


# Класс для валидации данных
class MessageValidate(BaseModel):
    """ Класс для валидации данных взятых из очереди logs в RabbitMQ

    Arguments:
        BaseModel {_type_} -- Базовый класс для валидации данных
    """
    project: str = Field(max_length=100, pattern=r'^[\w\s\-]+$')
    timestamp: datetime = Field(description="Timestamp в формате ISO 8601")
    level: Literal["info", "warning", "error", "fatal", "debug", "alert", "unknown"] = Field(max_length=10)  # Ограниченное множество возможных уровней
    module: str = Field(max_length=100)
    function: str = Field(max_length=100)
    message: str = Field(max_length=1000)
    code: int = Field(ge=0, le=999999)  # Приведение числа к строке с заполнением нулей слева до длины 6 символов

    class Config:
        title = "Message Log Schema"
        json_schema_extra = {
            "example": {
                "project": "home_logger",
                "timestamp": "2023-10-15T12:34:56Z",
                "level": "info",
                "module": "auth",
                "function": "login",
                "message": "User logged in successfully.",
                "code": 123
            }
        }


# Контекстная переменная для логгера
_current_logger_ctx_var: ContextVar[Optional["RabbitLogger"]] = ContextVar("current_logger", default=None)


# Получение актуального экземпляра логгера
def get_logger() -> "RabbitLogger":
    logger = _current_logger_ctx_var.get()
    if logger is None:
        raise RuntimeError("Логер не инициализирован. Используй 'async with initialize_logger(...)' для инициализации логера.")
    return logger


# Класс для логирования
class RabbitLogger:
    def __init__(self, config: LoggerConfig):
        self.config = config
        self.url = f"amqp://{config.username}:{config.password}@{config.host}:{config.port}/"
        
        self._connection: Optional[aio_pika.RobustConnection] = None
        self._channel: Optional[aio_pika.RobustChannel] = None
        self._queue: Optional[aio_pika.RobustQueue] = None
        self._context_token = None 

    async def __aenter__(self) -> "RabbitLogger":
        """ Функция для инициализации логгера

        Returns:
            RabbitLogger -- Объект логгера
        """
        
        await self._connect()
        self._context_token = _current_logger_ctx_var.set(self)
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        """ Функция для закрытия логгера

        Arguments:
            exc_type {_type_} -- Тип исключения, если возникло при выходе из контекста.
            exc_val {_type_} -- Исключение, если возникло при выходе из контекста.
            exc_tb {_type_} -- Traceback объекта, если возникло исключение.
        """
        
        if self._context_token is not None:
            _current_logger_ctx_var.reset(self._context_token)
        if self._connection:
            await self._connection.close()
            
    async def _connect(self) -> bool:
        """ Функция для подключения к RabbitMQ

        Returns:
            bool -- Статус подключения
        """
        
        if self._connection is not None:
            return True
        
        try:
            self._connection = await aio_pika.connect_robust(self.url)
            self._channel = await self._connection.channel()
            self._queue = await self._channel.declare_queue(
                self.config.queue,
                durable=True,
                arguments={"x-message-ttl": 30000}  # 30 секунд TTL
            )
            return True
        except Exception as e:
            print(f"Ошибка подключения к RabbitMQ: {e}")
            return False

    async def _send_message(self, message: dict) -> bool:
        """ Отправляет сообщение в очередь

        Arguments:
            message {dict} -- Данные сообщения

        Returns:
            bool -- Статус отправки
        """
        
        if self._queue is None:
            await self._connect()
            
        # Печать в консоль
        if self.config.console_enable:
            time_with_zone = datetime.fromisoformat(message['timestamp']).astimezone(self.config.console_time_zone)
            time_with_format = time_with_zone.strftime(self.config.console_time_format)
            print(
                f"[{time_with_format}] [{message['level'].upper()}] | "
                f"{message['module']} - {message['function']} | "
                f"{message['message']} | [{message['code']}]"
            )
            
        
        # Отправка в очередь RabbitMq    
        try:
            body = json.dumps(message, ensure_ascii=False).encode()
            await self._channel.default_exchange.publish(
                aio_pika.Message(body=body),
                routing_key=self.config.queue,
            )
            return True
        except Exception as e:
            print(f"Ошибка отправки лога в RabbitMq: {e}")
            return False

    async def _build_message(self, level: str, message: str, code: int) -> dict | None:
        """ Функция для формирования сообщения

        Arguments:
            level {str} -- Уровень лога ["info", "warning", "error", "fatal", "debug", "alert", "unknown"]
            message {str} -- Сообщение лога
            code {int} -- Код сообщения

        Returns:
            dict -- Сообщение лога
        """
        
        # Получение имени модуля и функции
        frame = inspect.currentframe()
        if frame and frame.f_back and frame.f_back.f_back:
            caller_frame = frame.f_back.f_back
            caller = inspect.getframeinfo(caller_frame)
            mod = caller.filename.split("/")[-1]
            func = caller.function
        else:
            mod = "unknown"
            func = "unknown"

        # Готовый словарь сообщения
        raw_message = {
            "project": self.config.project_name,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": level,
            "module": mod,
            "function": func,
            "message": message,
            "code": code,
        }
        
        # Валидация сообщения
        try:
            MessageValidate(**raw_message)
            return raw_message
        except Exception as e:
            print(f"Валидация не пройдена: {e}")
            return None

    async def info(self, message: str, code: int = 0) -> None:
        """ Функция для отправки лога в RabbitMQ со уровнем "INFO"

        Arguments:
            message {str} -- Сообщение лога

        Keyword Arguments:
            code {int} -- Код сообщения (default: {0})
        """
        
        result_message = await self._build_message("info", message, code)
        
        if result_message:
            await self._send_message(result_message)

    async def warning(self, message: str, code: int = 0) -> None:
        """ Функция для отправки лога в RabbitMQ со уровнем "WARNING"

        Arguments:
            message {str} -- Сообщение лога

        Keyword Arguments:
            code {int} -- Код сообщения (default: {0})
        """
        
        result_message = await self._build_message("warning", message, code)
        
        if result_message:
            await self._send_message(result_message)

    async def error(self, message: str, code: int = 0) -> None:
        """ Функция для отправки лога в RabbitMQ со уровнем "ERROR"

        Arguments:
            message {str} -- Сообщение лога

        Keyword Arguments:
            code {int} -- Код сообщения (default: {0})
        """
        
        result_message = await self._build_message("error", message, code)
        
        if result_message:
            await self._send_message(result_message)
        
    async def fatal(self, message: str, code: int = 0) -> None:
        """ Функция для отправки лога в RabbitMQ со уровнем "FATAL"

        Arguments:
            message {str} -- Сообщение лога

        Keyword Arguments:
            code {int} -- Код сообщения (default: {0})
        """
        
        result_message = await self._build_message("fatal", message, code)
        
        if result_message:
            await self._send_message(result_message)
    
    async def alert(self, message: str, code: int = 0) -> None:
        """ Функция для отправки лога в RabbitMQ со уровнем "ALERT"

        Arguments:
            message {str} -- Сообщение лога

        Keyword Arguments:
            code {int} -- Код сообщения (default: {0})
        """
        
        result_message = await self._build_message("alert", message, code)
        
        if result_message:
            await self._send_message(result_message)
        
    async def debug(self, message: str, code: int = 0) -> None:
        """ Функция для отправки лога в RabbitMQ со уровнем "DEBUG"

        Arguments:
            message {str} -- Сообщение лога

        Keyword Arguments:
            code {int} -- Код сообщения (default: {0})
        """
        
        result_message = await self._build_message("debug", message, code)
        
        if result_message:
            await self._send_message(result_message)
        
    async def unknown(self, message: str, code: int = 0) -> None:
        """ Функция для отправки лога в RabbitMQ со уровнем "UNKNOWN"

        Arguments:
            message {str} -- Сообщение лога

        Keyword Arguments:
            code {int} -- Код сообщения (default: {0})
        """
        
        result_message = await self._build_message("unknown", message, code)
        
        if result_message:
            await self._send_message(result_message)


# Инициализация логгера через контекстный менеджер
def initialize_logger(config: LoggerConfig) -> RabbitLogger:
    """ Инициализация логгера через контекстный менеджер

    Arguments:
        config {LoggerConfig} -- Настройки логгера {host, port, username, password, queue, project_name}

    Returns:
        RabbitLogger -- Объект логгера
    """
    return RabbitLogger(config)


# Пример использования
if __name__ == "__main__":
    async def main():
        from src.config import CurrentConfig as cfg  # type: ignore

        config = LoggerConfig(
            **cfg.rabbitmq,
            project_name="MyApp"
        )

        async with initialize_logger(config) as logger:
            _ = get_logger() # Получение логгера из контекста

            await logger.info("Application started")
            await logger.warning("This is a warning", code=1001)
            await logger.error("Something went wrong!")

            # Небольшая пауза, чтобы убедиться, что сообщения отправлены
            await asyncio.sleep(0.5)

    asyncio.run(main())