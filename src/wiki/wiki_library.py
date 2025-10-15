# app/src/wiki/wiki_library.py
# Модуль с описанием функций для работы с библиотекой

import asyncio
from src.lib.home_logger import init_logger, get_logger, LoggerConfig

# Пример использования
async def test_hui():
    
    # Конфигурация для старте логгера (Можно использовать частично)
    config = {
        "project_name": "Test",
        
        "rabbitmq": {
            "enabled": False,
        },
        "console": {
            "enabled": True,
        }
    }
    
    # Инициализация логгера и получение его экземпляра
    await init_logger(LoggerConfig(**config))
    lg = get_logger()

    # Пример использования логгера (code не обязательный аргумент, по стандарту 0)
    await lg.info("Информационное сообщение", code=100)
    await lg.warning("Сообщение о предупреждение")
    await lg.alert("Сигнальное сообщение", code=200)
    await lg.error("Сообщение об ошибке")
    await lg.fatal("Сообщение об аварии", code=300)
    await lg.debug("Сообщение о дебаге")
    await lg.unknown("Неизвестное сообщение", code=999999)


if __name__ == "__main__":
    asyncio.run(test_hui())
