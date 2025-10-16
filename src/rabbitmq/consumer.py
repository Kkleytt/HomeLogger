# app/src/consumer/consumer.py
# Модуль для получения данных из очереди RabbitMQ и перенаправления их в дочерние модули

import asyncio                  # Асинхронный запуск функций
import json                     # Работа с JSON строками
import aio_pika                 # Асинхронный движок для работы с RabbitMQ

from src.rabbitmq.message_validation import validate_message
from src.modules.write_to_database import Writer as DatabaseWriter
from src.modules.write_to_console import Writer as ConsoleWriter
from src.modules.write_to_files import Writer as FilesWriter
from src.models.config_models import ServerConfig
from src.config import CurrentConfig as cfg


GlobalConfig: ServerConfig
ConsoleClient: ConsoleWriter
DatabaseClient: DatabaseWriter
FilesClient: FilesWriter

# Генерация URL для подключения к RabbitMQ
async def generate_url(cfg: ServerConfig.RabbitMQ) -> str | None:
    if cfg.host and cfg.port and cfg.username and cfg.password:
        return f"amqp://{cfg.username}:{cfg.password}@{cfg.host}:{cfg.port}/"
    else:
        return None

# Логика обработки сообщения
async def distribution_message(message: aio_pika.IncomingMessage):


    # Читаем сообщение с автоматическим удалением после чтения
    async with message.process():
        
        # Распаковка сообщения
        dict_message: dict = json.loads(message.body.decode())
        
        # Валидация сообщения
        result_validation = await validate_message(dict_message)
        if not result_validation:
            raise Exception("Некорректные данные в сообщении!")
        
        # Запись сообщения в БД
        if GlobalConfig.timescaledb.enabled:
            await DatabaseClient.write_log(log=dict_message)
            
        # Запись в консоль
        if GlobalConfig.console.enabled:
            await ConsoleClient.print_log(dict_message)
            
        # Запись в файлы
        if GlobalConfig.files.enabled:
            await FilesClient.write_log(dict_message)

# Запуск наблюдателя
async def run_consumer(config: ServerConfig):
    global GlobalConfig
    global ConsoleClient
    global DatabaseClient
    global FilesClient

    GlobalConfig = config
    
    # Подключение к RabbitMq
    url = await generate_url(GlobalConfig.rabbitmq)
    connection = await aio_pika.connect_robust(url)
    channel = await connection.channel()

    # Создание очереди
    message_queue = await channel.declare_queue(
        GlobalConfig.rabbitmq.queue,
        durable=True,
        auto_delete=False,
        arguments={"x-message-ttl": 30000}
    )

    # Подписываемся на callback рассылку
    consume_tag = await message_queue.consume(distribution_message) # type: ignore
    
    # Подключение к консоли
    ConsoleClient = ConsoleWriter(GlobalConfig.console)
    
    # Подключение к БД
    DatabaseClient = DatabaseWriter(GlobalConfig.timescaledb)
    
    # Подключение к файлам
    FilesClient = FilesWriter(GlobalConfig.files)

    # Бесконечный цикл проверки сообщений
    try:
        print("[Logger] Запущен consumer. Ожидание сообщений...")
        while True:
            await asyncio.sleep(1)

    # Безопасная остановка наблюдателя
    finally:
        await message_queue.cancel(consume_tag)
        await channel.close()
        await connection.close()
        await FilesClient.close_all()
        
    
# Пример использования    
if __name__ == "__main__":
    config = {
        "rabbitmq": cfg.rabbitmq,
        "console": cfg.local_console,
        "timescaledb": cfg.timescaledb
    }
    asyncio.run(run_consumer(ServerConfig(**config))) # type: ignore
