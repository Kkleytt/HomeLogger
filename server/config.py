# app/src/config.py
# Модуль для получения параметров окружения

from dotenv import load_dotenv
from pathlib import Path
import os

class Config:
    def __init__(self, environment: str = ".env.test", folder_environments: str = ".env"):
        """ Функция для загрузки переменных окружения

        Keyword Arguments:
            environment {str} -- Имя переменного окружения (default: {"test"})
            folder_environments {str} -- Имя папки с переменными окружения (default: {".env"})
        """
        
        load_dotenv(dotenv_path=Path(__file__).parent / folder_environments / environment)

    @property
    def rabbitmq(self) -> dict:
        """ Функция для получения словаря с конфигурациями для подключения к RabbitMQ

        Returns:
            dict -- Словарь с конфигурациями для подключения к RabbitMQ
        """
        
        return {
            "host": os.getenv("RABBITMQ_HOST", "localhost"),
            "port": int(os.getenv("RABBITMQ_PORT", 5672)),
            "username": os.getenv("RABBITMQ_USERNAME", "logger"),
            "password": os.getenv("RABBITMQ_PASSWORD", "logger"),
            "queue": os.getenv("RABBITMQ_QUEUE", "logger")
        }
        
    @property
    def timescaledb(self) -> dict:
        """ Функция для получения словаря с конфигурациями для подключения к TimescaleDB

        Returns:
            dict -- Словарь с конфигурациями для подключения к TimescaleDB
        """
        
        return {
            "enabled": os.getenv("TIMESCALEDB_ENABLED", False),
            "host": os.getenv("TIMESCALEDB_HOST", "localhost"),
            "port": int(os.getenv("TIMESCALEDB_PORT", 5432)),
            "username": os.getenv("TIMESCALEDB_USERNAME", "logger"),
            "password": os.getenv("TIMESCALEDB_PASSWORD", "logger"),
            "database": os.getenv("TIMESCALEDB_DATABASE", "logger")
        }
        
    @property
    def logger(self) -> dict:
        """ Функция для получения словаря с конфигурациями логирования

        Returns:
            dict -- Словарь с конфигурациями логирования для библиотеки
        """
        
        return {
            "project_name": os.getenv("PROJECT_NAME", "DefaultProject"),
        }
        
    @property
    def local_console(self) -> dict:
        """ Функция для получения словаря с конфигурациями консольного логирования

        Returns:
            dict -- Словарь с конфигурациями консольного логирования
        """
        
        return {
            "enabled": os.getenv("CONSOLE_ENABLED", True),
            "format": os.getenv("CONSOLE_FORMAT", "[{project}] [{timestamp}] [{level}] {module}.{function}: {message} [{code}]"),
            "project_style": os.getenv("CONSOLE_PROJECT_STYLE", "bold cyan"),
            "timestamp_style": os.getenv("CONSOLE_TIMESTAMP_STYLE", "dim cyan"),
            "level_styles": {
                "info": os.getenv("CONSOLE_LEVEL_INFO_STYLE", "bold magenta"),
                "warning": os.getenv("CONSOLE_LEVEL_WARNING_STYLE", "bold yellow"),
                "error": os.getenv("CONSOLE_LEVEL_ERROR_STYLE", "bold red"),
                "fatal": os.getenv("CONSOLE_LEVEL_FATAL_STYLE", "bold white on red"),
                "debug": os.getenv("CONSOLE_LEVEL_DEBUG_STYLE", "dim cyan"),
                "alert": os.getenv("CONSOLE_LEVEL_ALERT_STYLE", "bold magenta"),
                "unknown": os.getenv("CONSOLE_LEVEL_UNKNOWN_STYLE", "")
            },
            "module_style": os.getenv("CONSOLE_MODULE_STYLE", "green"),
            "function_style": os.getenv("CONSOLE_FUNCTION_STYLE", "magenta"),
            "message_style": os.getenv("CONSOLE_MESSAGE_STYLE", ""),
            "code_style": os.getenv("CONSOLE_CODE_STYLE", "dim"),
            "time_format": os.getenv("CONSOLE_TIME_FORMAT", "%Y-%m-%d %H:%M:%S"),
            "time_zone": os.getenv("CONSOLE_TIME_ZONE", "UTC")
        }
    
    @property
    def files(self) -> dict:
        """ Функция для получения словаря с конфигурациями файлового логирования

        Returns:
            dict -- Словарь с конфигурациями файлового логирования
        """
        
        return {
            "enabled": os.getenv("FILES_ENABLED", True),
            "shared_directory": os.getenv("FILES_SHARED_DIRECTORY", "logs"),
            "project_directory": os.getenv("FILES_PROJECT_DIRECTORY", "{project}"),
            "filename": os.getenv("FILES_FILENAME", "log_{project}_{date}.log"),
            "date_file_format": os.getenv("FILES_DATE_FILE_FORMAT", "%Y-%m-%d_%H-%M-%S"),
            "date_log_format": os.getenv("FILES_DATE_LOG_FORMAT", "%Y-%m-%d %H:%M:%S"),
            "date_timezone": os.getenv("FILES_DATE_TIMEZONE", "UTC"),
            "log_format": os.getenv("FILES_LOG_FORMAT", "[{timestamp}] [{level}] {module}.{function}: {message} [{code}]"),
            "rotation": {
                "trigger": os.getenv("FILES_ROTATION_TRIGGER", "daily"),
                "time": int(os.getenv("FILES_ROTATION_TIME", 24400)),
                "daily": os.getenv("FILES_ROTATION_DAILY", "00:00"),
                "size": int(os.getenv("FILES_ROTATION_SIZE", 10485760)),
                "lines": int(os.getenv("FILES_ROTATION_LINES", 10000))
            },
            "archive": {
                "enabled": os.getenv("FILES_ARCHIVE_ENABLED", False),
                "type": os.getenv("FILES_ARCHIVE_TYPE", "zip"),
                "compression_level": int(os.getenv("FILES_ARCHIVE_COMPRESSION_LEVEL", 6)),
                "directory": os.getenv("FILES_ARCHIVE_DIRECTORY", "archive"),
                "trigger": os.getenv("FILES_ARCHIVE_TRIGGER", "count"),
                "count": int(os.getenv("FILES_ARCHIVE_COUNT", 10)),
                "age": int(os.getenv("FILES_ARCHIVE_AGE", 244000))
            }
        }

    

    def get_all_config(self) -> dict:
        """ Функция для получения полного словаря с конфигурациями

        Returns:
            dict -- Словарь с конфигурациями проекта
        """
        
        return {
            "rabbitmq": self.rabbitmq,
            "timescaledb": self.timescaledb,
            "logger": self.logger,
            "console": self.local_console,
            "files": self.files
        }

TestConfig = Config(".env.test")            # Конфигурация для тестов
ProductionConfig = Config(".env.prod")      # Конфигурация для продакшена
ExampleConfig = Config(".env.example")      # Конфигурация для примера
CurrentConfig = TestConfig                  # Текущая конфигурация