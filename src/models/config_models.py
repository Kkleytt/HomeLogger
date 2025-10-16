from pydantic import BaseModel, Field, IPvAnyAddress
from typing import Optional, Union, Literal
from zoneinfo import ZoneInfo



class ServerConfig(BaseModel):
    class TimescaleDB(BaseModel):        
        enabled: bool = True
        
        host: Union[IPvAnyAddress, Literal["localhost"]] = "localhost"
        port: Optional[int] = Field(ge=1, le=65535, description="TCP/UDP port (1-65535)", default=5432)
        username: Optional[str] = Field(default="logger")
        password: Optional[str] = Field(default="logger")
        database: Optional[str] = Field(default="logger")

    class RabbitMQ(BaseModel):
        host: Union[IPvAnyAddress, Literal["localhost"]] = "localhost"
        port: Optional[int] = Field(ge=1, le=65535, description="TCP/UDP port (1-65535)", default=5672)
        username: Optional[str] = Field(default="guest")
        password: Optional[str] = Field(default="guest")
        queue: Optional[str] = Field(default="logs")
    
    class Console(BaseModel):
        class Levels(BaseModel):
            info: str = Field(default="bold magenta")
            warning: str = Field(default="bold yellow")
            error: str = Field(default="bold red")
            fatal: str = Field(default="bold white on red")
            debug: str = Field(default="dim cyan")
            alert: str = Field(default="bold magenta")
            unknown: str = Field(default="bold white on red")
            
        enabled: bool = Field(default=True)
        format: str = Field(default="[{project}] [{timestamp}] [{level}] {module}.{function}: {message} [{code}]")
        
        project_style: str = Field(default="bold cyan")
        timestamp_style: str = Field(default="dim cyan")
        level_styles: Levels = Field(default_factory=Levels)
        module_style: str = Field(default="green")
        function_style: str = Field(default="magenta")
        message_style: str = Field(default="")
        code_style: str = Field(default="dim")
        
        time_format: str = Field(default="%Y-%m-%d %H:%M:%S")
        time_zone: ZoneInfo = Field(default_factory=lambda: ZoneInfo("UTC"))
        
    class Files(BaseModel):
        class Rotation(BaseModel):
            trigger: Literal["time", "size", "daily", "lines"] = Field(default="daily")
            time: int = Field(default=24400, ge=3600) # Время в секундах (24 часа)
            daily: str = Field(default="00:00") # Время в формате HH:MM
            size: int = Field(default=10 * 1024 * 1024, ge=1024) # Размер файла в байтах (10 МБ)
            lines: int = Field(default=10000) # Количество строк в файле
        
        class Archive(BaseModel):
            enabled: bool = Field(default=False)
            
            type: Literal["zip", "tar", "gz", "bz2", "xz"] = Field(default="zip")
            format: str = Field(default="{project}_{date}.{type}")
            compression_level: int = Field(ge=0, le=9, default=6)
            directory: str = Field(default="archive")
            
            trigger: Literal["age", "count"] = Field(default="count")
            count: int = Field(ge=1, default=10) # Количество старых файлов
            age: int = Field(default=10 * 24400, ge=24400) # Возраст файла (10 дней)
            
        enabled: bool = Field(default=False)
        
        share_directory: str = Field(default="logs")
        project_directory: str = Field(default="{project}")
        filename: str = Field(default="log_{project}_{date}.log")
        date_file_format: str = Field(default="%Y-%m-%d_%H-%M-%S")
        date_log_format: str = Field(default="%Y-%m-%d %H:%M:%S")
        date_timezone: str = Field(default="UTC")
        log_format: str = Field(default="[{project}] [{timestamp}] [{level}] {module}.{function}: {message} [{code}]")
        
        rotation: Rotation = Field(default_factory=Rotation)
        archive: Archive = Field(default_factory=Archive)
    
    rabbitmq: RabbitMQ = Field(default_factory=RabbitMQ)
    timescaledb: TimescaleDB = Field(default_factory=TimescaleDB)
    console: Console = Field(default_factory=Console)
    files: Files = Field(default_factory=Files)
    
    class Config:
        extra = "forbid"


# Класс для валидации настроек библиотеки
class LibraryConfig(BaseModel):
    """ Класс для валидации настроек библиотеки

    Arguments:
        BaseModel {_type_} -- Базовый класс для валидации данных
    """
    
    class Rabbit(BaseModel):
        enabled: bool = Field(default=False)
        host: Union[IPvAnyAddress, Literal["localhost"]] = "localhost"
        port: int = Field(ge=1, le=65535, description="TCP/UDP port (1-65535)", default=5672)
        username: str = Field(default="guest")
        password: str = Field(default="guest")
        queue: str = Field(default="logs")
       
    class Console(BaseModel):   
        class Levels(BaseModel):
            info: str = "bold magenta"
            warning: str = "bold yellow"
            error: str = "bold red"
            fatal: str = "bold white on red"
            debug: str = "dim cyan"
            alert: str = "bold magenta"
            unknown: str = "bold white on red"
    
        enabled: bool = True
        format: str = "[{timestamp}] [{level}] {module}.{function}: {message} [{code}]"
        
        timestamp_style: str = Field(default="dim cyan")
        level_styles: Levels = Field(default_factory=Levels)
        module_style: str = Field(default="green")
        function_style: str = Field(default="magenta")
        message_style: str = Field(default="")
        code_style: str = Field(default="dim")
        
        time_format: str = Field(default="%Y-%m-%d %H:%M:%S")
        time_zone: ZoneInfo = Field(default_factory=lambda: ZoneInfo("UTC"))
    
    project_name: str = Field(default="DefaultProject")
    rabbitmq: Rabbit = Field(default_factory=Rabbit)
    console: Console = Field(default_factory=Console)
    

    class Config:
        extra = "forbid"