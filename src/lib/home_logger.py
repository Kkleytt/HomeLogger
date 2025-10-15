# app/src/lib/home_logger.py
# Библиотека для логирования сообщений в RabbitMQ

import inspect
from typing import Optional, Literal, Dict, Any, Union
from pydantic import BaseModel, Field
from contextvars import ContextVar
from datetime import datetime, timezone
from zoneinfo import ZoneInfo
import aio_pika
import json
import os
import re

from rich.console import Console
from rich.text import Text


# Класс для валидации настроек стилей у уровней
class LevelStyles(BaseModel):
    """ Класс для валидации настроек стилей у уровней логирования

    Arguments:
        BaseModel {_type_} -- Базовый класс для валидации данных
    """
    
    info: str = "bold magenta"
    warning: str = "bold yellow"
    error: str = "bold red"
    fatal: str = "bold white on red"
    debug: str = "dim cyan"
    alert: str = "bold magenta"
    unknown: str = "bold white on red"

    class Config:
        extra = "forbid"

# Класс для валидации настроек логирования к консоль
class ConsoleConfig(BaseModel):
    """ Класс для валидации настроек логирования к консоль

    Arguments:
        BaseModel {_type_} -- Базовый класс для валидации данных
    """
    
    enabled: bool = True
    format: str = "[{timestamp}] [{level}] {module}.{function}: {message} [{code}]"
    
    timestamp_style: str = "dim cyan"
    level_styles: LevelStyles = Field(default_factory=LevelStyles)
    module_style: str = "green"
    function_style: str = "magenta"
    message_style: str = ""
    code_style: str = "dim"
    
    time_format: str = "%Y-%m-%d %H:%M:%S"
    time_zone: ZoneInfo = Field(default_factory=lambda: ZoneInfo("Europe/London"))

    class Config:
        extra = "forbid"

# Класс для валидации настроек логирования в RabbitMQ
class RabbitMQConfig(BaseModel):
    """ Класс для валидации настроек логирования в RabbitMQ

    Arguments:
        BaseModel {_type_} -- Базовый класс для валидации данных
    """
    
    enabled: bool = False
    
    host: Optional[str] = None
    port: Optional[int] = None
    username: Optional[str] = None
    password: Optional[str] = None
    queue: Optional[str] = None
    
    class Config:
        extra = "forbid"

# Класс для валидации сообщений
class MessageValidate(BaseModel):
    """ Класс для валидации сообщения перед отправкой в RabbitMQ

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

# Класс для валидации конфигурации логера
class LoggerConfig(BaseModel):
    """ Класс для валидации конфигурации логера

    Arguments:
        BaseModel {_type_} -- Базовый класс для валидации данных
    """
    
    # --- Общие настройки проекта (Обязательные) ---
    project_name: str

    # --- Настройки логирования в RabbitMQ 
    rabbitmq: RabbitMQConfig = Field(default_factory=RabbitMQConfig)
    
    # Настройки логирования в консоль
    console: ConsoleConfig = Field(default_factory=ConsoleConfig)

    class Config:
        extra = "forbid"


# Контекстная переменная для логгера
_current_logger_ctx_var: ContextVar[Optional["RabbitLogger"]] = ContextVar("current_logger", default=None)


# Получение актуального экземпляра логгера
def get_logger() -> "RabbitLogger":
    """ Функция для получения текущего экземпляра логгера

    Raises:
        RuntimeError: Ошибка при попытке получить логгер, если он не инициализирован

    Returns:
        RabbitLogger -- Класс логгера
    """
    
    logger = _current_logger_ctx_var.get()
    if logger is None:
        raise RuntimeError("Логер не инициализирован. Используй 'async with initialize_logger(...)' для инициализации логера.")
    return logger


# Класс для логирования
class RabbitLogger:
    def __init__(self, config: LoggerConfig):
        self.config = config
        self.url = f"amqp://{config.rabbitmq.username}:{config.rabbitmq.password}@{config.rabbitmq.host}:{config.rabbitmq.port}/"
        
        self._connection: Optional[aio_pika.RobustConnection] = None
        self._channel: Optional[aio_pika.RobustChannel] = None
        self._queue: Optional[aio_pika.RobustQueue] = None
        self._context_token = None 
        
        self.Console = Console()

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
        
        if self.config.rabbitmq.enabled:
            try:
                self._connection = await aio_pika.connect_robust(self.url) # type: ignore
                self._channel = await self._connection.channel() # type: ignore
                self._queue = await self._channel.declare_queue( # type: ignore
                    self.config.rabbitmq.queue,
                    durable=True,
                    arguments={"x-message-ttl": 30000}  # 30 секунд TTL
                )
                return True
            except Exception as e:
                print(f"Ошибка подключения к RabbitMQ: {e}")
                return False
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
        if self.config.console.enabled:
            self.Console.print(await self._render_log(message))
        
        # Если нужно передавать лог в очередь
        if self.config.rabbitmq.enabled:
            try:
                body = json.dumps(message, ensure_ascii=False).encode()
                await self._channel.default_exchange.publish( # type: ignore
                    aio_pika.Message(body=body),
                    routing_key=self.config.queue # type: ignore
                )
                return True
            except Exception as e:
                print(f"Ошибка отправки лога в RabbitMq: {e}")
                return False
        
        return True

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
            caller_frame = frame.f_back.f_back.f_back
            caller = inspect.getframeinfo(caller_frame) # type: ignore
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

    async def _log(self, level: str, message: str, code: int = 0) -> bool:
        """ Функция для отправки лога в RabbitMQ

        Arguments:
            level {str} -- Уровень лога
            message {str} -- Сообщение лога

        Keyword Arguments:
            code {int} -- Код сообщения (default: {0})

        Returns:
            bool -- Статус отправки
        """
        
        result_message = await self._build_message(level, message, code)
        
        if result_message:
            return await self._send_message(result_message) # type: ignore
        else:
            return False
            
    async def _render_log(self, message: dict) -> Text:
        """ Функция для форматирования сообщения в консоль

        Arguments:
            message {dict} -- JSON сообщение

        Returns:
            Text -- Отформатированное сообщение для библиотеки rich
        """
        config = self.config.console
        
        # Преобразуем строку в datetime, если нужно
        dt = datetime.fromisoformat(message["timestamp"])
        dt = dt.astimezone(config.time_zone)        
        ts_str = dt.strftime(config.time_format)
        
        data = {
            "timestamp": Text(ts_str, style=config.timestamp_style),
            "level": Text(
                message["level"].upper(),
                style=getattr(
                    config.level_styles,
                    message["level"],
                    config.level_styles.unknown
                )
            ),
            "module": Text(message["module"], style=config.module_style),
            "function": Text(message["function"], style=config.function_style),
            "message": Text(message["message"], style=config.message_style),
            "code": Text(str(message["code"]), style=config.code_style),
        }
        
        output = Text()
        format_str = config.format
        
        parts = re.split(r"\{(\w+)\}", format_str)
        for part in parts:
            if part in data:
                output.append(data[part])
            elif part:
                output.append(part)
        
        return output
    
    async def info(self, message: str, code: int = 0) -> bool:
        """ Функция для отправки лога в RabbitMQ со уровнем "INFO"

        Arguments:
            message {str} -- Сообщение лога

        Keyword Arguments:
            code {int} -- Код сообщения (default: {0})

        Returns:
            bool -- Статус отправки
        """
        
        return await self._log("info", message, code) 
    
    async def warning(self, message: str, code: int = 0) -> bool:
        """ Функция для отправки лога в RabbitMQ со уровнем "WARNING"

        Arguments:
            message {str} -- Сообщение лога

        Keyword Arguments:
            code {int} -- Код сообщения (default: {0})

        Returns:
            bool -- Статус отправки
        """
        
        return await self._log("warning", message, code) 
    
    async def error(self, message: str, code: int = 0) -> bool:
        """ Функция для отправки лога в RabbitMQ со уровнем "ERROR"

        Arguments:
            message {str} -- Сообщение лога

        Keyword Arguments:
            code {int} -- Код сообщения (default: {0})

        Returns:
            bool -- Статус отправки
        """
        
        return await self._log("error", message, code) 
    
    async def fatal(self, message: str, code: int = 0) -> bool:
        """ Функция для отправки лога в RabbitMQ со уровнем "FATAL"

        Arguments:
            message {str} -- Сообщение лога

        Keyword Arguments:
            code {int} -- Код сообщения (default: {0})

        Returns:
            bool -- Статус отправки
        """
        
        return await self._log("fatal", message, code) 
    
    async def alert(self, message: str, code: int = 0) -> bool:
        """ Функция для отправки лога в RabbitMQ со уровнем "ALERT"

        Arguments:
            message {str} -- Сообщение лога

        Keyword Arguments:
            code {int} -- Код сообщения (default: {0})

        Returns:
            bool -- Статус отправки
        """
        
        return await self._log("alert", message, code) 
    
    async def debug(self, message: str, code: int = 0) -> bool:
        """ Функция для отправки лога в RabbitMQ со уровнем "DEBUG"

        Arguments:
            message {str} -- Сообщение лога

        Keyword Arguments:
            code {int} -- Код сообщения (default: {0})

        Returns:
            bool -- Статус отправки
        """
        
        return await self._log("debug", message, code) 
    
    async def unknown(self, message: str, code: int = 0) -> bool:
        """ Функция для отправки лога в RabbitMQ со уровнем "UNKNOWN"

        Arguments:
            message {str} -- Сообщение лога

        Keyword Arguments:
            code {int} -- Код сообщения (default: {0})

        Returns:
            bool -- Статус отправки
        """
        
        return await self._log("unknown", message, code) 

# Инициализация логгера через контекстный менеджер
async def init_logger(config: LoggerConfig) -> RabbitLogger:
    """ Инициализация логгера через контекстный менеджер

    Arguments:
        config {LoggerConfig} -- Настройки логгера {host, port, username, password, queue, project_name}

    Returns:
        RabbitLogger -- Объект логгера
    """
    
    logger = RabbitLogger(config)
    await logger._connect()
    token = _current_logger_ctx_var.set(logger)
    logger._context_token = token
    return logger