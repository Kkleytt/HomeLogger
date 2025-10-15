# app/src/tests/test_consumer.py
# Модуль для отправки сообщений в очередь RabbitMQ

import asyncio
import json
from datetime import datetime, timezone
from aio_pika import connect_robust, Message # type: ignore

from src.config import CurrentConfig as config
from src.models.config_models import LibraryConfig

message_body = {"project": "home_logger", "timestamp": "2023-10-15T12:34:56Z", "level": "info", "module": "auth", "function": "login", "message": "User logged in successfully.", "code": 123}

async def generate_url(config: LibraryConfig.Rabbit) -> str | None:
    if config.host and config.port and config.username and config.password:
        return f"amqp://{config.username}:{config.password}@{config.host}:{config.port}/"
    else:
        return None


async def send_messages(config: LibraryConfig.Rabbit, interval_seconds: int):
    connection = await connect_robust(await generate_url(config))
    async with connection:
        channel = await connection.channel()
        queue = await channel.declare_queue(config.queue, durable=True, arguments={"x-message-ttl": 30000})

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
        asyncio.run(send_messages(LibraryConfig.Rabbit(**config.rabbitmq), 10))  # Отправляем сообщения каждые 10 секунд
    except Exception as ex:
        print(ex)
    finally:
        exit(0)
        