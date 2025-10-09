# app/src/run.py
# Модуль для запуска проекта

import asyncio

from src.consumer.consumer import run_consumer
from src.config import CurrentConfig as cfg


async def main():
    
    # Запуск consumer
    await run_consumer(**cfg.rabbitmq)
    

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("[!] Остановка по Ctrl+C")
    finally:
        exit(0)