# consumer.py
# Модуль для получения данных из очереди RabbitMQ и перенаправления их в дочерние модули

import asyncio                  # Асинхронный запуск функций
import json                     # Работа с JSON строками
import aio_pika                 # Асинхронный движок для работы с RabbitMQ


# Параметры подключения
config = {
    "host": "localhost",
    "port": 2201,
    "username": "logger",
    "password": "logger",
}


async def generate_url(host: str, port: int, username: str, password: str) -> str | None:
    if host and port and username and password:
        return f"amqp://{username}:{password}@{host}:{port}/"
    else:
        return None


# Логика обработки логов
async def distribution_logs(message: aio_pika.IncomingMessage):

    # Читаем сообщение с автоматическим удалением после чтения
    async with message.process():

        # Распаковка сообщения
        message = json.loads(message.body.decode())
        
        print(message)


async def main():
    # Подключение к RabbitMq
    connection = await aio_pika.connect_robust(await generate_url(**config))
    channel = await connection.channel()

    # Создание очереди
    logs_queue = await channel.declare_queue(
        "logs",
        durable=True,
        auto_delete=False,
        arguments={"x-message-ttl": 30000}
    )

    # Подписываемся на callback рассылку
    consume_tag = await logs_queue.consume(distribution_logs) # type: ignore

    # Бесконечный цикл проверки сообщений
    try:
        print("[Logger] Запущен consumer. Ожидание сообщений...")
        while True:
            await asyncio.sleep(1)

    # Безопасная остановка наблюдателя
    finally:
        await logs_queue.cancel(consume_tag)
        await channel.close()
        await connection.close()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("[!] Остановка по Ctrl+C")
    except Exception as e:
        print(f"[!] Ошибка при запуске consumer: {e}")
