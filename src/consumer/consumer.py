# app/src/consumer/consumer.py
# Модуль для получения данных из очереди RabbitMQ и перенаправления их в дочерние модули

import asyncio                  # Асинхронный запуск функций
import json                     # Работа с JSON строками
import aio_pika                 # Асинхронный движок для работы с RabbitMQ

from src.config import CurrentConfig as cfg
from src.consumer.message_validation import validate_message
from src.modules.write_to_database import write_to_database




# Генерация URL для подключения к RabbitMQ
async def generate_url(host: str, port: int, username: str, password: str) -> str | None:
    if host and port and username and password:
        return f"amqp://{username}:{password}@{host}:{port}/"
    else:
        return None

# Логика обработки сообщения
async def distribution_message(message: aio_pika.IncomingMessage):


    # Читаем сообщение с автоматическим удалением после чтения
    async with message.process():
        
        # Распаковка сообщения
        message: dict = json.loads(message.body.decode())
        print(message)
        
        # Валидация сообщения
        result_validation = await validate_message(message) # type: ignore
        if not result_validation:
            raise Exception("Некорректные данные в сообщении!")
        
        # Перенаправление сообщения в дочерние модули
        await write_to_database(log_message=message)
        #await LOG_DB.insert_log(model=generate_log_model(message['project']), log=message)

# Запуск наблюдателя
async def run_consumer(host: str, port: int, username: str, password: str, queue: str):
    
    # Подключение к RabbitMq
    url = await generate_url(host, port, username, password)
    connection = await aio_pika.connect_robust(url)
    channel = await connection.channel()

    # Создание очереди
    message_queue = await channel.declare_queue(
        queue,
        durable=True,
        auto_delete=False,
        arguments={"x-message-ttl": 30000}
    )

    # Подписываемся на callback рассылку
    consume_tag = await message_queue.consume(distribution_message) # type: ignore

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
        
    
# Пример использования    
if __name__ == "__main__":
    asyncio.run(run_consumer(**cfg.rabbitmq))
