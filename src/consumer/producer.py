import asyncio
import json
import time
from aio_pika import connect_robust, Message # type: ignore

# Настройки RabbitMQ
config = {
    'host': 'localhost',
    'port': 2201,
    'username': 'logger',
    'password': 'logger',
}
name_queue = "logs"
message_body = {"timestamp": None, "event": "Test event"}

async def generate_url(host: str, port: int, username: str, password: str) -> str | None:
    if host and port and username and password:
        return f"amqp://{username}:{password}@{host}:{port}/"
    else:
        return None


async def send_messages(interval_seconds: int):
    connection = await connect_robust(await generate_url(**config))
    async with connection:
        channel = await connection.channel()
        queue = await channel.declare_queue(name_queue, durable=True, arguments={"x-message-ttl": 30000})

        while True:
            current_time = time.time()
            message_body["timestamp"] = current_time
            serialized_message = json.dumps(message_body)
            message = Message(body=serialized_message.encode(), content_type='application/json')

            await channel.default_exchange.publish(message, routing_key=queue.name)
            print(f"Sent message at {current_time}: {serialized_message}")

            await asyncio.sleep(interval_seconds)

if __name__ == '__main__':
    try:
        asyncio.run(send_messages(10))  # Отправляем сообщения каждые 10 секунд
    finally:
        exit(0)