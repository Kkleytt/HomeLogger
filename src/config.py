# app/src/config.py
# Модуль для получения параметров окружения

from dotenv import load_dotenv
from pathlib import Path
import os

class Config:
    def __init__(self, environment: str = "test", folder_environments: str = ".env"):
        """ Функция для загрузки переменных окружения

        Keyword Arguments:
            environment {str} -- Имя переменного окружения (default: {"test"})
            folder_environments {str} -- Имя папки с переменными окружения (default: {".env"})
        """
        
        load_dotenv(dotenv_path=Path(__file__).parent / folder_environments / f".env.{environment}")

    @property
    def rabbitmq(self):
        return {
            "host": os.getenv("RABBITMQ_HOST", "localhost"),
            "port": int(os.getenv("RABBITMQ_PORT", "5672")),
            "username": os.getenv("RABBITMQ_USERNAME", "logger"),
            "password": os.getenv("RABBITMQ_PASSWORD", "logger"),
            "queue": os.getenv("RABBITMQ_QUEUE", "logger")
        }
        
    @property
    def logger(self):
        return {
            "project_name": os.getenv("LOGGER_PROJECT", "DefaultProject"),
            
            "print_to_console": os.getenv("LOGGER_PRINT_TO_CONSOLE", "True"),
            "console_time_format": os.getenv("LOGGER_CONSOLE_TIME_FORMAT", "%Y-%m-%d %H:%M:%S"),
            "console_time_zone": os.getenv("LOGGER_CONSOLE_TIME_ZONE", "Europe/London"),
            
            "send_to_server": os.getenv("LOGGER_SEND_TO_SERVER", "True"),
            "host": os.getenv("LOGGER_HOST", "localhost"),
            "port": int(os.getenv("LOGGER_PORT", "5672")),
            "username": os.getenv("LOGGER_USERNAME", "logger"),
            "password": os.getenv("LOGGER_PASSWORD", "logger"),
            "queue": os.getenv("LOGGER_QUEUE", "logger")
        }

    @property
    def timescaledb(self):
        return {
            "host": os.getenv("TIMESCALEDB_HOST", "localhost"),
            "port": int(os.getenv("TIMESCALEDB_PORT", "5432")),
            "username": os.getenv("TIMESCALEDB_USERNAME", "logger"),
            "password": os.getenv("TIMESCALEDB_PASSWORD", "logger"),
            "database": os.getenv("TIMESCALEDB_DATABASE", "logger")
        }

    def get_all_config(self) -> dict:
        """ Функция для получения полного словаря с конфигурациями

        Returns:
            dict -- Словарь с конфигурациями проекта
        """
        
        return {
            "rabbitmq": self.rabbitmq,
            "logger": self.logger,
            "timescaledb": self.timescaledb
        }


TestConfig = Config("test")         # Конфигурация для тестов
ProductionConfig = Config("prod")   # Конфигурация для продакшена
CurrentConfig = TestConfig          # Текущая конфигурация