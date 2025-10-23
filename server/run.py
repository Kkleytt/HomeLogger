# server/run.py (или main.py)

import asyncio
import uvicorn
import signal
import logging

from server.config.config import ConfigManager as cfg
from server.config.logging import setup_logging
from server.rabbitmq.consumer import RabbitMQConsumer
from server.api.api import fastapi
from server.rabbitmq.errors import ExceptionRabbitMQ


# --- Настройка логгера ---
setup_logging()
logger = logging.getLogger(__name__)

# --- Глобальные переменные для управления ---
consumer_task: asyncio.Task | None = None
shutdown_event = asyncio.Event()

async def run_consumer() -> None:
    """
    Запуск модуля RabbitMQ Consumer.
    """
    
    consumer = RabbitMQConsumer()
    try:
        await consumer.run_forever()
    except (ExceptionRabbitMQ.StartError, ExceptionRabbitMQ.StopError, ExceptionRabbitMQ.ConfigUpdateError, ExceptionRabbitMQ.ModuleError) as e:
        logger.critical(f"Критическая ошибка в Consumer, работа завершена: {e}")
        # Здесь можно добавить логику уведомления, отчет об ошибке и т.д.
    except KeyboardInterrupt:
        logger.info("Получен сигнал KeyboardInterrupt, завершение.")
    except Exception as e:
        logger.critical(f"Необработанная ошибка верхнего уровня: {e}", exc_info=True)

def run_api() -> None:
    """
    Запуск REST-full API.
    """
    try:
        uvicorn.run(
            fastapi,  # Передаём экземпляр приложения, а не функцию
            host=str(cfg.config.api.host),
            port=cfg.config.api.port,
            reload=True,
            
        )
    except Exception as e:
        logging.error(f"Ошибка при запуске API: {e}", exc_info=True)
        

async def shutdown_handler():
    """
    Обработчик сигнала остановки.
    """
    
    shutdown_event.set()

    # Отменяем задачу consumer
    global consumer_task
    if consumer_task:
        consumer_task.cancel()
        try:
            await consumer_task
        except asyncio.CancelledError:
            pass # Ожидаемое поведение

async def run_modules():
    """
    Основная асинхронная функция для запуска модулей.
    """
    global consumer_task

    # Регистрируем обработчики сигналов для корректной остановки
    # Это позволяет корректно завершить программу по Ctrl+C
    loop = asyncio.get_running_loop()
    for sig in (signal.SIGTERM, signal.SIGINT):
        loop.add_signal_handler(sig, lambda: asyncio.create_task(shutdown_handler()))

    # Запускаем Consumer как асинхронную задачу
    consumer_task = asyncio.create_task(run_consumer())
    
    await asyncio.sleep(1)

    # Попробуем так:
    if cfg.config.api.enabled:
        logging.info("Запуск API...")
        server_config = uvicorn.Config(
            fastapi,
            host=str(cfg.config.api.host),
            port=cfg.config.api.port,
            log_level="info",
            reload=True
        )
        server = uvicorn.Server(server_config)

        # Запускаем сервер как асинхронную задачу
        api_task = asyncio.create_task(server.serve())

        # Ждём, пока один из сервисов не завершится 
        await asyncio.gather(api_task, consumer_task, return_exceptions=True)
    else:
        logging.info("API отключен в параметрах конфигурации")
        await consumer_task # Ждём завершения consumer

if __name__ == "__main__":
    asyncio.run(run_modules())