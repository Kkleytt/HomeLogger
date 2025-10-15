from rich.console import Console
from rich.text import Text
from datetime import datetime
import re

from src.models.config_models import ServerConfig

class Writer:
    def __init__(self, config: ServerConfig.Console):
        self.config = config
        self.Console = Console()

    async def _render_log(self, message: dict) -> Text:
        """ Функция для форматирования сообщения в консоль

        Arguments:
            message {dict} -- JSON сообщение

        Returns:
            Text -- Отформатированное сообщение для библиотеки rich
        """
        
        # Преобразуем строку в datetime, если нужно
        dt = datetime.fromisoformat(message["timestamp"])
        dt = dt.astimezone(self.config.time_zone)        
        ts_str = dt.strftime(self.config.time_format)
        
        data = {
            "project": Text(message["project"], style=self.config.project_style),
            "timestamp": Text(ts_str, style=self.config.timestamp_style),
            "level": Text(
                message["level"].upper(),
                style=getattr(
                    self.config.level_styles,
                    message["level"],
                    self.config.level_styles.unknown
                )
            ),
            "module": Text(message["module"], style=self.config.module_style),
            "function": Text(message["function"], style=self.config.function_style),
            "message": Text(message["message"], style=self.config.message_style),
            "code": Text(str(message["code"]), style=self.config.code_style),
        }
        
        output = Text()
        format_str = self.config.format
        
        parts = re.split(r"\{(\w+)\}", format_str)
        for part in parts:
            if part in data:
                output.append(data[part])
            elif part:
                output.append(part)
        
        return output
    
    async def print_log(self, message: dict) -> None:
        self.Console.print(await self._render_log(message))
            

            