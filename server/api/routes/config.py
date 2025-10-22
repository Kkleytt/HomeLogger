from fastapi import APIRouter, HTTPException
from pydantic import ValidationError
from aio_pika import connect_robust, Message
import json

from server.config.schema import ServerConfig
from server.config.config import ConfigManager as cfg

router = APIRouter()

async def send_update_config(new_config_data: dict) -> None:
    """ Функция для отправки обновлённой конфигурации в очередь

    Arguments:
        new_config_data {dict} -- Новая конфигурация
    """
    
    async def generate_url() -> str | None:
        """ Функция для генерации URL для подключения к RabbitMQ

        Returns:
            str | None -- URL для подключения к RabbitMQ или None, если не все параметры конфигурации указаны
        """
        
        config = cfg.config.api.rabbitmq
        if config.host and config.port and config.username and config.password:
            return f"amqp://{config.username}:{config.password}@{config.host}:{config.port}/"
        else:
            return None
    
    connection = await connect_robust(await generate_url())
    async with connection:
        channel = await connection.channel()
        queue = await channel.declare_queue("service_queue", durable=True, arguments={"x-message-ttl": 30000})
        
        message_body = {
            "code": 100,
            "detail": "Update config",
            "data": new_config_data
        }
        serialized_message = json.dumps(message_body)
        message = Message(body=serialized_message.encode(), content_type='application/json')
        await channel.default_exchange.publish(message, routing_key=queue.name)

@router.get("/config", response_model=ServerConfig, description="Получение текущей конфигурации проекта")
async def get_current_config():
    """ Маршрут для получения текущей конфигурации проекта

    Returns:
        ServerConfig -- Актуальная конфигурация проекта
    """
    
    return cfg.config

@router.put("/config", response_model=ServerConfig, description="Обновление конфигурации проекта")
async def update_config(new_config: dict):
    """ Маршрут для обновления конфигурации проекта

    Arguments:
        new_config {dict} -- Новая конфигурация проекта

    Returns:
        ServerConfig -- Новая конфигурация проекта
    """
    
    try:
        validation_data = ServerConfig(**new_config)        # Проверяем валидность данных
        await cfg.update_config(new_config_data=new_config) # Обновляем конфигурацию
        await send_update_config(new_config)                # Отправляем обновлённую конфигурацию в очередь
        return validation_data                              # Возвращаем обновлённую конфигурацию
    
    except ValidationError as e:
        print(f"Error validating new config: {e}")
        return HTTPException(status_code=400, detail="Error validation new config")
    
    except Exception as e:
        print(f"Error updating config: {e}")
        return HTTPException(status_code=500, detail="Internal Server Error")