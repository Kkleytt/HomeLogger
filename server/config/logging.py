# server/logging.py
# Настройки логирования для библиотеки logging

import logging
import sys
from datetime import datetime

# --- Кастомный Formatter, имитирующий стиль uvicorn с именем логгера ---
class UvicornStyleFormatter(logging.Formatter):
    """
    Кастомный форматтер, имитирующий стиль логов uvicorn,
    но добавляющий имя логгера.
    """
    def format(self, record):
        # Получаем время в формате HH:MM:SS
        time_str = datetime.fromtimestamp(record.created).strftime('%H:%M:%S')
        # Получаем уровень лога (INFO, ERROR и т.д.)
        level_str = record.levelname
        # Получаем имя логгера (например, server.consumer.consumer)
        name_str = record.name
        # Получаем сообщение
        msg_str = record.getMessage()

        # Формируем строку в стиле uvicorn + имя логгера
        # [HH:MM:SS] LEVEL: NAME - MESSAGE
        formatted_message = f"[{time_str}] {level_str}:     {name_str} - {msg_str}"

        # Если есть traceback, добавляем его
        if record.exc_info:
            formatted_message += "\n" + self.formatException(record.exc_info)

        return formatted_message

def setup_logging():
    """
    Настраивает корневой логгер и форматтер для uvicorn-стиля с именем логгера.
    """
    # Создаём форматтер
    formatter = UvicornStyleFormatter()

    # Получаем корневой логгер
    root_logger = logging.getLogger()

    # Удаляем все существующие обработчики, чтобы избежать дублирования
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)

    # Создаём обработчик для вывода в stdout
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(formatter)

    # Добавляем обработчик к корневому логгеру
    root_logger.addHandler(handler)

    # Устанавливаем минимальный уровень для корневого логгера
    root_logger.setLevel(logging.INFO)