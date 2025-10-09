# app/src/tests/test_consumer.py
# Модуль для отправки сообщений в очередь RabbitMQ

import asyncio
import json
from datetime import datetime, timezone
from aio_pika import connect_robust, Message # type: ignore

from src.config import CurrentConfig as cfg

message_body = {"project": "home_logger", "timestamp": "2023-10-15T12:34:56Z", "level": "info", "module": "auth", "function": "login", "message": "User logged in successfully.", "code": 123}

async def generate_url(host: str, port: int, username: str, password: str, queue: str) -> str | None:
    if host and port and username and password:
        return f"amqp://{username}:{password}@{host}:{port}/"
    else:
        return None


async def send_messages(interval_seconds: int):
    connection = await connect_robust(await generate_url(**cfg.rabbitmq))
    async with connection:
        channel = await connection.channel()
        queue = await channel.declare_queue(cfg.rabbitmq['queue'], durable=True, arguments={"x-message-ttl": 30000})

        while True:
            current_time = str(datetime.now(timezone.utc))
            message_body["timestamp"] = current_time
            serialized_message = json.dumps(message_body)
            message = Message(body=serialized_message.encode(), content_type='application/json')

            await channel.default_exchange.publish(message, routing_key=queue.name)
            print(f"Sent message at {current_time}: {serialized_message}")

            await asyncio.sleep(interval_seconds)

if __name__ == '__main__':
    try:
        print('start')
        asyncio.run(send_messages(10))  # Отправляем сообщения каждые 10 секунд
    except Exception as ex:
        print(ex)
    finally:
        exit(0)