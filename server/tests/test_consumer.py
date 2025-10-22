# app/server/tests/test_consumer.py
# Модуль для отправки сообщений в очередь RabbitMQ

import asyncio
import json
from datetime import datetime, timezone
from aio_pika import connect_robust, Message

from server.config.config import ConfigManager as cfg
from server.config.schema import LibraryConfig

message_body = {"project": "home_logger", "timestamp": "2023-10-15T12:34:56Z", "level": "info", "module": "auth", "function": "login", "message": "User logged in successfully.", "code": 123}

async def generate_url(cfg: LibraryConfig.Rabbit) -> str | None:
    if cfg.host and cfg.port and cfg.username and cfg.password:
        return f"amqp://{cfg.username}:{cfg.password}@{cfg.host}:{cfg.port}/"
    else:
        return None


async def send_messages(cfg: LibraryConfig.Rabbit, interval_seconds: int):
    connection = await connect_robust(await generate_url(cfg))
    async with connection:
        channel = await connection.channel()
        queue = await channel.declare_queue(cfg.queue, durable=True, arguments={"x-message-ttl": 30000})

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
        asyncio.run(send_messages(LibraryConfig.Rabbit(**cfg.config.rabbitmq.model_dump()), 10))
    except Exception as ex:
        print(f"Error - {ex}")
    finally:
        exit(0)
        