# app/server/models/config_models.py
# Класс для валидации настроек сервера

from pydantic import BaseModel, Field, IPvAnyAddress
from typing import Optional, Union, Literal



class ServerConfig(BaseModel):
    """ Класс для валидации настроек сервера

    Arguments:
        BaseModel {_type_} -- Базовый класс для валидации данных
    """
    
    class TimescaleDB(BaseModel):        
        """ Класс для валидации настроек подключения в TimescaleDB

        Arguments:
            BaseModel {_type_} -- Базовый класс для валидации данных
        """
        
        enabled: bool = Field(default=True, description="Статус активации логирования в TimescaleDB")
        
        host: Union[IPvAnyAddress, Literal["localhost"]] = Field(default="localhost", description="Ip адрес или имя хоста для подключения к TimescaleDB")
        port: Optional[int] = Field(ge=1, le=65535, default=5432, description="Порт для подключения к TimescaleDB")
        username: Optional[str] = Field(default="logger", description="Имя пользователя для подключения к TimescaleDB")
        password: Optional[str] = Field(default="logger", description="Пароль для подключения к TimescaleDB")
        database: Optional[str] = Field(default="logger", description="База данных для подключения к TimescaleDB")

    class RabbitMQ(BaseModel):
        """ Класс для валидации настроек подключения в RabbitMQ

        Arguments:
            BaseModel {_type_} -- Базовый класс для валидации данных
        """
        
        host: Union[IPvAnyAddress, Literal["localhost"]] = Field(default="localhost", description="Ip адрес или имя хоста для подключения к RabbitMQ")
        port: Optional[int] = Field(ge=1, le=65535, default=5672, description="Порт для подключения к RabbitMQ")
        username: Optional[str] = Field(default="guest", description="Имя пользователя для подключения к RabbitMQ")
        password: Optional[str] = Field(default="guest", description="Пароль для подключения к RabbitMQ")
        queue: Optional[str] = Field(default="logs", description="Очередь для получения логов в RabbitMQ")
    
    class Logger(BaseModel):
        project_name: str = Field(default="DefaultProject", description="Имя проекта для логирования")
    
    class Console(BaseModel):
        """ Класс для валидации настроек логирования в консоль

        Arguments:
            BaseModel {_type_} -- Базовый класс для валидации данных
        """
        
        class Levels(BaseModel):
            """ Класс для валидации настроек стилей у уровней логирования

            Arguments:
                BaseModel {_type_} -- Базовый класс для валидации данных
            """
            
            info: str = Field(default="bold magenta", description="Rich стили для вывода уровня лога INFO")
            warning: str = Field(default="bold yellow", description="Rich стили для вывода уровня лога WARNING")
            error: str = Field(default="bold red", description="Rich стили для вывода уровня лога ERROR")
            fatal: str = Field(default="bold white on red", description="Rich стили для вывода уровня лога FATAL")
            debug: str = Field(default="dim cyan", description="Rich стили для вывода уровня лога DEBUG")
            alert: str = Field(default="bold magenta", description="Rich стили для вывода уровня лога ALERT")
            unknown: str = Field(default="bold white on red", description="Rich стили для вывода уровня лога UNKNOWN")
            
        enabled: bool = Field(default=True, description="Статус активации логирования в консоль")
        format: str = Field(default="[{project}] [{timestamp}] [{level}] {module}.{function}: {message} [{code}]", description="Формат лог-записи при выводе в консоль")
        
        project_style: str = Field(default="bold cyan", description="Rich стили для вывода имени проекта")
        timestamp_style: str = Field(default="dim cyan", description="Rich стили для вывода даты и времени лога-записи")
        level_styles: Levels = Field(default_factory=Levels, description="Rich стили для вывода уровней лога-записи")
        module_style: str = Field(default="green", description="Rich стили для вывода имени модуля лога-записи")
        function_style: str = Field(default="magenta", description="Rich стили для вывода имени функции лога-записи")
        message_style: str = Field(default="", description="Rich стили для вывода сообщения лога-записи")
        code_style: str = Field(default="dim", description="Rich стили для вывода кода лога-записи")
        
        time_format: str = Field(default="%Y-%m-%d %H:%M:%S", description="Формат даты и времени при выводе в консоль")
        time_zone: str = Field(default="UTC", description="Часовой пояс для форматирования времени")
        
    class Files(BaseModel):
        """ Класс для валидации настроек логирования в файлы

        Arguments:
            BaseModel {_type_} -- Базовый класс для валидации данных
        """
        
        class Rotation(BaseModel):
            """ Класс для валидации настроек смены файла логирования

            Arguments:
                BaseModel {_type_} -- Базовый класс для валидации данных
            """
            
            trigger: Literal["time", "size", "daily", "lines"] = Field(default="daily", description="Триггер для смены файла логирования (time, size, daily, lines)")
            time: int = Field(default=24400, ge=3600, description="Возраст лог-файла для активации триггера смены файла")
            daily: str = Field(default="00:00", description="Время в формате 24H для активации триггера смены файла")
            size: int = Field(default=10 * 1024 * 1024, ge=1024, description="Размер файла для активации триггера смены файла")
            lines: int = Field(default=10000, description="Количество лог-записей для активации триггера смены файла")
            
        class Archive(BaseModel):
            """ Класс для валидации настроек архивации лог-файлов

            Arguments:
                BaseModel {_type_} -- Базовый класс для валидации данных
            """
            
            enabled: bool = Field(default=False, description="Статус активации архивации лог-файлов")
            
            type: Literal["zip", "tar", "gz", "bz2", "xz"] = Field(default="zip", description="Тип архива для сжатия (zip, tar, gz, bz2, xz)")
            compression_level: int = Field(ge=0, le=9, default=6, description="Уровень сжатия архивов (0-9)")
            directory: str = Field(default="archive", description="Директория для хранения архивов")
            
            trigger: Literal["age", "count"] = Field(default="count", description="Триггер для активации архивации лог-файлов")
            count: int = Field(ge=1, default=10, description="Количество старых файлов для активации триггера архивации")
            age: int = Field(default=10 * 24400, ge=24400, description="Возраст файла для активации триггера архивации (в секундах)")
            
        enabled: bool = Field(default=True, description="Статус активации логирования в файлы")
        
        shared_directory: str = Field(default="logs", description="Общая директория для хранения лог-файлов")
        project_directory: str = Field(default="{project}", description="Паттерн для имени директории проекта")
        filename: str = Field(default="log_{project}_{date}.log", description="Паттерн имени файла")
        date_file_format: str = Field(default="%Y-%m-%d_%H-%M-%S", description="Формат даты в имени файла")
        date_log_format: str = Field(default="%Y-%m-%d %H:%M:%S", description="Формат даты в лог-записях")
        date_timezone: str = Field(default="UTC", description="Часовой пояс для даты в формате ISO 8601")
        log_format: str = Field(default="[{project}] [{timestamp}] [{level}] {module}.{function}: {message} [{code}]", description="Формат лог-записи")
        
        rotation: Rotation = Field(default_factory=Rotation, description="Настройки смены файла для логирования записей")
        archive: Archive = Field(default_factory=Archive, description="Настройки архивации старых лог-файлов")
    
    rabbitmq: RabbitMQ = Field(default_factory=RabbitMQ, description="Настройки для подключения к RabbitMQ")
    timescaledb: TimescaleDB = Field(default_factory=TimescaleDB, description="Настройки для подключения к TimescaleDB")
    logger: Logger = Field(default_factory=Logger, description="Общие настройки логирования")
    console: Console = Field(default_factory=Console, description="Настройки для вывода логов в консоль")
    files: Files = Field(default_factory=Files, description="Настройки для логирования в файлы")
    
    class Config:
        extra = "forbid"


# Класс для валидации настроек библиотеки
class LibraryConfig(BaseModel):
    """ Класс для валидации настроек библиотеки

    Arguments:
        BaseModel {_type_} -- Базовый класс для валидации данных
    """
    
    class Rabbit(BaseModel):
        """ Класс для валидации настроек подключения к RabbitMQ

        Arguments:
            BaseModel {_type_} -- Базовый класс для валидации данных
        """
        
        enabled: bool = Field(default=False, description="Статус активации логирования в RabbitMQ")
        host: Union[IPvAnyAddress, Literal["localhost"]] = Field(default="localhost", description="Ip адрес или имя хоста для подключения к RabbitMQ")
        port: int = Field(ge=1, le=65535, default=5672, description="Порт для подключения к RabbitMQ")
        username: str = Field(default="guest", description="Имя пользователя для подключения к RabbitMQ")
        password: str = Field(default="guest", description="Пароль для подключения к RabbitMQ")
        queue: str = Field(default="logs", description="Очередь для логирования в RabbitMQ")
       
    class Console(BaseModel):  
        """ Класс для валидации настроек вывода логов в консоль

        Arguments:
            BaseModel {_type_} -- Базовый класс для валидации данных
        """
 
        class Levels(BaseModel):
            """ Класс для валидации настроек стилей у уровней логирования

            Arguments:
                BaseModel {_type_} -- Базовый класс для валидации данных
            """
            
            info: str = Field(default="bold magenta", description="Rich стили для вывода уровня лога INFO")
            warning: str = Field(default="bold yellow", description="Rich стили для вывода уровня лога WARNING")
            error: str = Field(default="bold red", description="Rich стили для вывода уровня лога ERROR")
            fatal: str = Field(default="bold white on red", description="Rich стили для вывода уровня лога FATAL")
            debug: str = Field(default="dim cyan", description="Rich стили для вывода уровня лога DEBUG")
            alert: str = Field(default="bold magenta", description="Rich стили для вывода уровня лога ALERT")
            unknown: str = Field(default="bold white on red", description="Rich стили для вывода уровня лога UNKNOWN")
    
        enabled: bool = Field(default=True, description="Статус активации логирования в консоль")
        format: str = Field(default="[{timestamp}] [{level}] {module}.{function}: {message} [{code}]", description="Паттерн вывода лог-записи в консоль")
        
        timestamp_style: str = Field(default="dim cyan", description="Rich стиль для вывода даты и времени")
        level_styles: Levels = Field(default_factory=Levels, description="Rich стили для вывода уровней лога")
        module_style: str = Field(default="green", description="Rich стиль для вывода имени модуля")
        function_style: str = Field(default="magenta", description="Rich стиль для вывода имени функции")
        message_style: str = Field(default="", description="Rich стиль для вывода сообщения")
        code_style: str = Field(default="dim", description="Rich стиль для вывода кода ошибки")
        
        time_format: str = Field(default="%Y-%m-%d %H:%M:%S", description="Формат даты и времени в лог-записях")
        time_zone: str = Field(default="UTC", description="Часовой пояс для даты в формате ISO 8601")
    
    project_name: str = Field(default="DefaultProject", description="Имя проекта для логирования")
    rabbitmq: Rabbit = Field(default_factory=Rabbit, description="Настройки для подключения к RabbitMQ")
    console: Console = Field(default_factory=Console, description="Настройки для вывода логов в консоль")
    

    class Config:
        extra = "forbid"