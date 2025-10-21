# app/src/config.py
# Модуль для получения параметров окружения

import asyncio
import os
import json
from dotenv import load_dotenv
from pathlib import Path
from pydantic import ValidationError
from typing import List, Callable, Dict, Any

from server.config.schema import ServerConfig


class Manager:
    def __init__(self, initial_config: ServerConfig):
        """
        Инициализирует ConfigManager с начальной конфигурацией.
        """
        self.config_file_path = Path(__file__).parent / "config.json"
        self._config: ServerConfig = initial_config
        self._callbacks: List[Callable[[ServerConfig], None]] = []
        self._lock = asyncio.Lock()  # Для thread-safe обновлений (в asyncio контексте)

    @property
    def config(self) -> ServerConfig:
        """
        Возвращает текущую конфигурацию.
        """
        return self._config

    def subscribe(self, callback: Callable[[ServerConfig], None]):
        """
        Подписывает функцию/метод на изменения конфигурации.
        """
        self._callbacks.append(callback)

    def unsubscribe(self, callback: Callable[[ServerConfig], None]):
        """
        Отписывает функцию/метод от изменений конфигурации.
        """
        if callback in self._callbacks:
            self._callbacks.remove(callback)

    async def update_config(self, new_config_data: dict) -> ServerConfig:
        """
        Обновляет конфигурацию, валидирует её и уведомляет подписчиков.
        """
        async with self._lock:
            try:
                # Валидируем новые данные и создаём новую модель
                validated_config = ServerConfig(**new_config_data)
                old_config = self._config
                self._config = validated_config

                # Уведомляем всех подписчиков ТОЛЬКО если конфиг изменился
                if old_config != self._config:
                    for callback in self._callbacks:
                        callback(self._config)
                        
                # Сохраняем конфигурацию в файл
                self._save_config_to_file(new_config_data)

                return self._config
            except ValidationError as e:
                print(f"❌ Ошибка валидации новой конфигурации: {e}")
                raise ValueError(f"Invalid configuration data: {e}")

    async def reload_from_source(self, source_loader_func):
        """
        (Опционально) Перезагружает конфигурацию из внешнего источника (например, файла, БД).
        """
        async with self._lock:
            try:
                raw_data = source_loader_func()
                validated_config = ServerConfig(**raw_data)
                old_config = self._config
                self._config = validated_config

                # Уведомляем подписчиков только если конфиг действительно изменился
                if old_config != self._config:
                    for callback in self._callbacks:
                        callback(self._config)

                return self._config
            except ValidationError as e:
                print(f"❌ Ошибка валидации перезагруженной конфигурации: {e}")
                raise ValueError(f"Invalid configuration data from source: {e}")

    def _save_config_to_file(self, config_dict: Dict[str, Any]) -> bool:
        """ Функция для сохранения конфигурации в файл

        Arguments:
            config_dict {Dict[str, Any]} -- JSON конфигурация

        Returns:
            bool -- Статус сохранения
        """
        
        try:
            with open(self.config_file_path, 'w', encoding='utf-8') as f:
                json.dump(config_dict, f, indent=2, ensure_ascii=False)
                
            return True
        except Exception as e:
            print(f"Error save config to json file: {e}")
            return False


class Config:
    def __init__(self, environment: str = ".env.test", folder_environments: str = ".env"):
        """ Функция для загрузки переменных окружения

        Keyword Arguments:
            environment {str} -- Имя переменного окружения (default: {"test"})
            folder_environments {str} -- Имя папки с переменными окружения (default: {".env"})
        """
        
        self.environment = environment
        self.folder_environments = folder_environments
        self._config_file_path = Path(__file__).parent / "config.json"

        # Загружаем .env файл
        load_dotenv(dotenv_path=Path(__file__).parent.parent / folder_environments / environment)

        # Загружаем конфигурацию
        self._config_dict = self._load_config()

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
    
    def _load_config(self) -> Dict[str, Any]:
        """ Функция для загрузки конфигурации из файла или переменного окружения

        Raises:
            e: Ошибка валидации конфигурации

        Returns:
            Dict[str, Any] -- Словарь с конфигурациями
        """
        
        if self._config_file_path.exists():
            try:
                with open(self._config_file_path, 'r', encoding='utf-8') as f:
                    raw_config = json.load(f)
                ServerConfig(**raw_config)
                return raw_config
            except Exception as e:
                return self._get_all_config()

        else:
            env_config = self._get_all_config()
            try:
                validated_env_config = ServerConfig(**env_config)
                self._save_config_to_file(validated_env_config.model_dump())
                return validated_env_config.model_dump()
            except Exception as e:
                print(f"❌ Ошибка валидации конфигурации из .env: {e}")
                raise e
    
    def _save_config_to_file(self, config_dict: Dict[str, Any]) -> bool:
        """ Функция для сохранения конфигурации в файл

        Arguments:
            config_dict {Dict[str, Any]} -- JSON конфигурация

        Returns:
            bool -- Статус сохранения
        """
        
        try:
            with open(self._config_file_path, 'w', encoding='utf-8') as f:
                json.dump(config_dict, f, indent=2, ensure_ascii=False)
                
            return True
        except Exception as e:
            print(f"Error save config to json file: {e}")
            return False
    
    def _get_all_config(self) -> Dict:
        """ Функция для получения полного словаря с конфигурациями

        Returns:
            Dict -- Словарь с параметрами
        """
        
        with open(self._config_file_path, 'r', encoding='utf-8') as f:
            raw_config = json.load(f)
        
        return raw_config

TestConfig = Config(".env.test")            # Конфигурация для тестов
ProductionConfig = Config(".env.prod")      # Конфигурация для продакшена
ExampleConfig = Config(".env.example")      # Конфигурация для примера
CurrentConfig = TestConfig                  # Текущая конфигурация (Изменять под разные окружения)


ConfigManager = Manager(ServerConfig(**CurrentConfig._get_all_config())) # Менеджер конфигураций
