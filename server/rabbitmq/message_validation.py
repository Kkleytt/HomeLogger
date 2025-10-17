# app/server/consumer/message_validation.py
# Модуль для валидации данных взятых из очереди logs в RabbitMQ

from datetime import datetime
from pydantic import BaseModel, Field, ValidationError
from typing import Literal


# Класс для валидации данных
class MessageValidate(BaseModel):
    """ Класс для валидации данных взятых из очереди logs в RabbitMQ

    Arguments:
        BaseModel {_type_} -- Базовый класс для валидации данных
    """
    project: str = Field(max_length=100, pattern=r'^[\w\s\-]+$')
    timestamp: datetime = Field(description="Timestamp в формате ISO 8601")
    level: Literal["info", "warning", "error", "fatal", "debug", "alert", "unknown"] = Field(max_length=10)  # Ограниченное множество возможных уровней
    module: str = Field(max_length=100)
    function: str = Field(max_length=100)
    message: str = Field(max_length=1000)
    code: int = Field(ge=0, le=999999)  # Приведение числа к строке с заполнением нулей слева до длины 6 символов

    class Config:
        title = "Message Log Schema"
        json_schema_extra = {
            "example": {
                "project": "home_logger",
                "timestamp": "2023-10-15T12:34:56Z",
                "level": "info",
                "module": "auth",
                "function": "login",
                "message": "User logged in successfully.",
                "code": 123
            }
        }


# Функция для валидации данных
async def validate_message(data: dict) -> dict | None:
    """ Функция для валидации данных взятых из очереди logs в RabbitMQ

    Arguments:
        data {dict} -- Данные для валидации

    Returns:
        dict | None -- Данные или None
    """
    
    try:
        valid_message = MessageValidate(**data)
        return valid_message.model_dump()
    except ValidationError as e:
        print(f"Validation Error: {e}")
        return None


# Пример использования
if __name__ == "__main__":
    invalid_data = {
        "project": "home-logger",
        "timestamp": "2023-10-25",
        "level": "info",
        "module": "auth",
        "function": "login",
        "message": "User logged in successfully.",
        "code": 1236567567576
    }
    correct_data = {
        "project": "home-logger",
        "timestamp": "2023-10-15T12:34:56Z",
        "level": "info",
        "module": "auth",
        "function": "login",
        "message": "User logged in successfully.",
        "code": 123
    }

    # Проверка неверных данных
    result = validate_message(invalid_data)
    print(f"Incorrect data validation is - {result}") 
    
    # Проверка верных данных
    result = validate_message(correct_data)
    print(f"Correct data validation is - {result}") 