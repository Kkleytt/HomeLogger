from pydantic import BaseModel, Field, field_validator, IPvAnyAddress
from typing import Optional, Union, Literal
from zoneinfo import ZoneInfo



class ServerConfig(BaseModel):
    class TimescaleDB(BaseModel):        
        enabled: bool = True
        
        host: Union[IPvAnyAddress, Literal["localhost"]] = "localhost"
        port: Optional[int] = Field(ge=1, le=65535, description="TCP/UDP port (1-65535)", default=5432)
        username: Optional[str] = "logger"
        password: Optional[str] = "logger"
        database: Optional[str] = "logger"

    class RabbitMQ(BaseModel):
        host: Union[IPvAnyAddress, Literal["localhost"]] = "localhost"
        port: Optional[int] = Field(ge=1, le=65535, description="TCP/UDP port (1-65535)", default=5672)
        username: Optional[str] = "guest"
        password: Optional[str] = "guest"
        queue: Optional[str] = "logs"
    
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
        format: str = "[{project_name}] [{timestamp}] [{level}] {module}.{function}: {message} [{code}]"
        
        timestamp_style: str = "dim cyan"
        level_styles: Levels = Field(default_factory=Levels)
        module_style: str = "green"
        function_style: str = "magenta"
        message_style: str = ""
        code_style: str = "dim"
        
        time_format: str = "%Y-%m-%d %H:%M:%S"
        time_zone: ZoneInfo = Field(default_factory=lambda: ZoneInfo("UTC"))
    
    rabbitmq: RabbitMQ = Field(default_factory=RabbitMQ)
    timescaledb: TimescaleDB = Field(default_factory=TimescaleDB)
    console: Console = Field(default_factory=Console)


# Класс для валидации настроек библиотеки
class LibraryConfig(BaseModel):
    """ Класс для валидации настроек библиотеки

    Arguments:
        BaseModel {_type_} -- Базовый класс для валидации данных
    """
    
    class Rabbit(BaseModel):
        enabled: bool = False
        host: Union[IPvAnyAddress, Literal["localhost"]] = "localhost"
        port: int = Field(ge=1, le=65535, description="TCP/UDP port (1-65535)", default=5672)
        username: str = "guest"
        password: str = "guest"
        queue: str = "logs"
       
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
        
        timestamp_style: str = "dim cyan"
        level_styles: Levels = Field(default_factory=Levels)
        module_style: str = "green"
        function_style: str = "magenta"
        message_style: str = ""
        code_style: str = "dim"
        
        time_format: str = "%Y-%m-%d %H:%M:%S"
        time_zone: ZoneInfo = Field(default_factory=lambda: ZoneInfo("UTC"))
    
    project_name: str = "DefaultProject"
    rabbitmq: Rabbit = Field(default_factory=Rabbit)
    console: Console = Field(default_factory=Console)
    

    class Config:
        extra = "forbid"