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