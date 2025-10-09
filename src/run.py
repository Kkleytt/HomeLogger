# app/src/run.py
# Модуль для запуска проекта

import asyncio

from src.rabbitmq.consumer import run_consumer
from src.config import CurrentConfig as cfg


async def main():
    
    # Запуск consumer
    await run_consumer(**cfg.rabbitmq)
    

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("[!] Остановка по Ctrl+C")
    except Exception as ex:
        print(f"Ошибка: {ex}")
    finally:
        exit(0)