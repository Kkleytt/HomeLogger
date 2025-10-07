# test_client.py
# Модуль для тестирования клиента базы данных

import pytest
import asyncio
from datetime import datetime, timedelta
from sqlalchemy.orm import declarative_base
from sqlalchemy import Column, Integer, String

from postgres_client import Client 


config = {
    "host": "localhost",
    "port": 2200,
    "username": "logger",
    "password": "logger",
    "database": "logger",
}

Base = declarative_base()
class BaseModel(Base):
    __tablename__ = "test_table"
    id = Column(Integer, primary_key=True)
    name = Column(String)
    
    
# Тест на подключение к базе данных
@pytest.mark.asyncio
async def test_connect_success():
    client = Client(**config)
    assert await client.connect() is True
    assert client.connected is True

# Тест на отключение от базы данных
@pytest.mark.asyncio
async def test_disconnect():
    client = Client(**config)
    await client.connect()
    assert await client.disconnect() is True
    assert client.connected is False
    
# Тест на проверку подключения
@pytest.mark.asyncio
async def test_is_connected():
    client = Client(**config)
    await client.connect()
    assert await client.connect_state() is True
    client._last_check = datetime.now() - timedelta(minutes=31)
    assert await client.connect_state() is True  # Переподключение
    

# Тест на добавление таймера на переподключение
@pytest.mark.asyncio
async def test_add_timer_reconnect():
    client = Client(**config)

    # Проверка включения таймера
    result = await client.add_timer_reconnect(interval=30, state=True)
    assert result is True
    assert isinstance(client._reconnect_interval, timedelta)
    assert client._reconnect_interval.total_seconds() == 30 * 60  # 30 минут
    assert client._reconnect_state is True

    # Проверка выключения таймера
    result = await client.add_timer_reconnect(state=False)
    assert result is False
    assert client._reconnect_state is False
    

# Тест на создание таблицы
@pytest.mark.asyncio
async def test_create_table():
    client = Client(**config)
    await client.connect()
    assert await client.create_table_if_not_exists(BaseModel) is True
    

# Тест на добавление модели в базу данных (one)
@pytest.mark.asyncio
async def test_insert_model_one():
    client = Client(**config)
    await client.connect()
    result = await client.insert_model(BaseModel, [{"name": "Fedora99"}])
    assert result.name == "Fedora99" # type: ignore
    print(result)


# Тест на добавление модели в базу данных (many)
@pytest.mark.asyncio
async def test_insert_model_many():
    client = Client(**config)
    await client.connect()
    result = await client.insert_model(BaseModel, [{"name": "Fedora99"}, {"name": "Fedora98"}], fetch_many=True)#type: ignore
    assert result[0].name == "Fedora99" # type: ignore
    assert result[1].name == "Fedora98" # type: ignore
    

# Тест на выборку модели из базы данных (one)
@pytest.mark.asyncio
async def test_select_model_one():
    client = Client(**config)
    await client.connect()
    await client.insert_model(BaseModel, [{"name": "Alice"}])
    result = await client.select_model(BaseModel, BaseModel.name == "Alice")
    print(result)
    assert result.name == "Alice" # type: ignore
    
    
# Тест на выборку модели из базы данных (many)
@pytest.mark.asyncio
async def test_select_model_many():
    client = Client(**config)
    await client.connect()
    await client.insert_model(BaseModel, [{"name": "Alice many"}, {'name': 'Alice many'}], fetch_many=True)
    result = await client.select_model(BaseModel, BaseModel.name == "Alice many", fetch_many=True)
    assert result[0].name == "Alice many" # type: ignore


# Тест на обновление записи (one)
@pytest.mark.asyncio
async def test_update_record_one():
    client = Client(**config)
    await client.connect()
    await client.insert_model(BaseModel, [{"name": "Charlie"}])
    record = await client.select_model(BaseModel, BaseModel.name == "Charlie")
    record_id = record.id # type: ignore
    result = await client.update_record_partition(BaseModel, BaseModel.id == record_id, new_data={"name": "Charlie Updated One"})
    assert result.name == "Charlie Updated One" # type: ignore
    

# Тест на обновление записи (many)
@pytest.mark.asyncio
async def test_update_record_many():
    client = Client(**config)
    await client.connect()
    await client.insert_model(BaseModel, [{"name": "Charlie"}, {'name': 'Charlie'}], fetch_many=True)
    result = await client.update_record_partition(BaseModel, BaseModel.name == "Charlie", new_data={"name": "Charlie Updated Many"}, fetch_many=True)
    assert result[0].name == "Charlie Updated Many" # type: ignore


# Тест на удаление записи (one)
@pytest.mark.asyncio
async def test_delete_record_one():
    client = Client(**config)
    await client.connect()
    await client.insert_model(BaseModel, [{"name": "Dave"}])
    record = await client.select_model(BaseModel, BaseModel.name == "Dave")
    record_id = record.id # type: ignore
    result = await client.delete_record(BaseModel, BaseModel.id == record_id)
    assert result.name == "Dave" # type: ignore
    assert await client.select_model(BaseModel, BaseModel.id == record_id) == None
    
# Тест на удаление записи (many)
@pytest.mark.asyncio
async def test_delete_record_many():
    client = Client(**config)
    await client.connect()
    await client.insert_model(BaseModel, [{"name": "Dave"}, {'name': 'Dave'}], fetch_many=True)
    result = await client.delete_record(BaseModel, BaseModel.name == "Dave", fetch_many=True)
    assert result[0].name == "Dave" # type: ignore
    assert await client.select_model(BaseModel, BaseModel.name == "Dave") == None
    

# Тест на выполнение произвольного SQL-запроса (one)
@pytest.mark.asyncio
async def test_manual_execute_one(): 
    client = Client(**config)
    await client.connect()
    result = await client.manual_execute("SELECT * FROM test_table WHERE name = 'Charlie Updated One'")
    assert result["name"] == "Charlie Updated One" # type: ignore

# Тест на выполнение произвольного SQL-запроса (many)
@pytest.mark.asyncio
async def test_manual_execute_many(): 
    client = Client(**config)
    await client.connect()
    result = await client.manual_execute("SELECT * FROM test_table WHERE name = 'Charlie Updated One'", fetch_many=True)
    assert result[0]["name"] == "Charlie Updated One" # type: ignore
    
# Тест на сброс базы данных
@pytest.mark.asyncio
async def test_remove_all_data(): 
    client = Client(**config)
    await client.connect()
    result = await client.manual_execute("DELETE FROM test_table", response=False)
    assert result == None # type: ignore

async def test_piska():
    client = Client(**config)
    await client.connect()
    await test_insert_model_many()
    result = await client.manual_execute("SELECT * FROM test_table WHERE name = 'Fedora99'", fetch_many=False)
    assert result["name"] == "Fedora99" # type: ignore
    await client.disconnect()
    
    
if __name__ == "__main__":
    asyncio.run(test_piska())
    