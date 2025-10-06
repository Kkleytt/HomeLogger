import asyncio
from datetime import datetime, timedelta
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker, declarative_base
from sqlalchemy import Column, Integer, String, text

from client import Client

config = {
    "host": "46.160.250.162",
    "port": 2251,
    "username": "logger",
    "password": "logger",
    "database": "logger"
}
class TestModel(declarative_base()):
    __tablename__ = "test_table"
    id = Column(Integer, primary_key=True)
    name = Column(String)


async def main():
    
    #### Подключение к базе данных
    client = Client(**config)
    a = await client.connect()
    print(f"Подключение к базе данных: {a}")
    
    #### Проверка соединения
    a = await client.connect_state()
    print(f"Проверка соединения к базе данных: {a}")

    #### Добавление таймера
    a = await client.add_timer_reconnect(40, True)
    print(f"Добавление таймера: {a}")
    
    #### Получение параметров клиента
    a = await client.get_settings()
    print(f"Получение параметров клиента: {a}")

    #### Создание таблицы
    a = await client.create_table_if_not_exists(TestModel)
    print(f"Создание таблицы: {a}")
    
    #### Запись в таблицу (one)
    a = await client.insert_model(TestModel, [{'name': 'Fedora'}])
    print(f"Запись в таблицу: {a}")
    
    #### Запись в таблицу (many)
    a = await client.insert_model(TestModel, [{'name': 'Fedora'}, {'name': 'Fedora-2'}], fetch_many=True)
    print(f"Запись в таблицу: {a}")
    
    #### Выборка из таблицы (one)
    a = await client.select_model(TestModel, TestModel.name == 'Fedora')
    print(f"Выборка из таблицы (one): {a}")
    
    #### Выборка из таблицы (many)
    a = await client.select_model(TestModel, TestModel.name == 'Fedora', fetch_many=True)
    print(f"Выборка из таблицы (many): {a}")
    
    #### Обновление записи в таблице (one)
    a = await client.update_record_partition(TestModel, TestModel.name == 'Fedora', new_data={'name': 'Fedora Updated'})
    print(f"Обновление записи в таблице: {a}")
    
    #### Обновление записи в таблице (many)
    a = await client.update_record_partition(TestModel, TestModel.name == 'Fedora', new_data={'name': 'Fedora Updated'}, fetch_many=True)
    print(f"Обновление записи в таблице: {a}")
    
    #### Выполнение произвольного SQL-запроса (one)
    query = "SELECT id FROM test_table WHERE name = :name"
    a = await client.manual_execute(query, {'name': 'Fedora Updated'})
    print(f"Выполнение произвольного SQL-запроса: {a}")
    
    #### Выполнение произвольного SQL-запроса (many)
    query = "SELECT id FROM test_table WHERE name = :name"
    a = await client.manual_execute(query, {'name': 'Fedora Updated'}, fetch_many=True)
    print(f"Выполнение произвольного SQL-запроса: {a}")
    
    #### Удаление записи из таблицы
    a = await client.delete_record(TestModel, TestModel.name == 'Fedora Updated')
    print(f"Удаление записи из таблицы: {a}")
    
    #### Закрытие сессии
    a = await client.disconnect()
    print(f"Закрытие сессии: {a}")
    
    



if __name__ == "__main__":
    asyncio.run(main())