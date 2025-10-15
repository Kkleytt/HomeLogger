from datetime import datetime, timezone, timedelta
from zoneinfo import ZoneInfo
from typing import Dict, Optional
from pydantic import BaseModel, Field
import os
import re

from rich.console import Console
from rich.text import Text


console_config = {
    # Единый шаблон с плейсхолдерами
    "format": "[{timestamp}] [{level}] {module}.{function}: {message} [{code}]",
    
    # Стили для каждого поля (Rich-совместимые строки)
    "styles": {
        "timestamp": "dim cyan",
        "level": {
            "info": "bold white",
            "warning": "bold yellow",
            "error": "bold red",
            "fatal": "bold white on red",
            "debug": "dim cyan",
            "alert": "bold magenta",
            "unknown": "dim"
        },
        "module": "green",
        "function": "magenta",
        "message": "",
        "code": "dim"
    },
    
    # Настройки времени
    "time_format": "%H:%M:%S",
    "time_zone": "UTC+3",
    
    # Включено ли
    "enabled": True
}

    
log = {
    "timestamp": datetime.now(timezone.utc).astimezone(ZoneInfo("Europe/Moscow")).strftime("%Y-%m-%d %H:%M:%S"),
    "level": "info",
    "module": "main",
    "function": "main",
    "message": "This is a test log message",
    "code": 200
}




def render_log(message: dict, config: dict) -> Text:
    # 1. Форматируем время
    dt = datetime.now(timezone.utc).astimezone(ZoneInfo("Europe/Moscow"))
    ts_str = dt.strftime(config["time_format"])
    
    # 2. Подготавливаем данные с применением стилей
    data = {
        "timestamp": Text(ts_str, style=config["styles"]["timestamp"]),
        "level": Text(
            message["level"].upper(),
            style=config["styles"]["level"][message["level"]]
        ),
        "module": Text(message["module"], style=config["styles"]["module"]),
        "function": Text(message["function"], style=config["styles"]["function"]),
        "message": Text(message["message"], style=config["styles"]["message"]),
        "code": Text(str(message["code"]), style=config["styles"]["code"]),
    }
    
    # 3. Собираем строку вручную (из-за Text)
    output = Text()
    format_str = config["format"]
    
    # Простой парсер: разбиваем по {field}
    parts = re.split(r"\{(\w+)\}", format_str)
    for part in parts:
        if part in data:
            output.append(data[part])
        elif part:
            output.append(part)
    
    return output

# Вывод
console = Console()
console.print(render_log(log, console_config))



# Возможные значения стилей в конфиге
# foreground - цвет текста [black, red, green, yellow, blue, magenta, cyan, white]
# background - цвет подложки [on black, on red, on green, on yellow, on blue, on magenta, on cyan, on white]
# styles - стили текста [bold, dim, italic, underline, blink, reverse, strike]
