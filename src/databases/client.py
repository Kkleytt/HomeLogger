# Класс для работы с PostgreSQL базами данных, ориентированный на использование совместно в логгером
# Класс должен иметь следующие возможности:
# 1) Проверка соединения, подключение, отключение, инициализация
# 2) Работа с моделями: создание таблицы, получение данных, добавление данных, удаление данных, изменение данных
# 3) Работа с фильтрацией: добавление фильтров к запросам завязанных на моделях
# #   4) Ручные запросы, исключительно SQL запрос и переменные для него
# Также класс должен быть устойчивым, быстрым и стабильным, работать асинхронно и использовать SqlAlchemy, жесткую типизацию и оптимизацию всех процессов
# Сложность     - 6/10
# Начало работ  - 01.10.2025
# Дедлайн       - 10.10.2025 (9 дней)

from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Type, Union
from urllib.parse import quote_plus

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.sql import text


class Client:
    def __init__(self, host: str, port: int, username: str, password: str, database: str) -> None:
        # Установка значений переменных
        self.host = host
        self.port = port
        self.username = username
        self.password = password
        self.database = database

        # Служебные переменные
        self.connected = False
        self.engine = None
        self.async_session: Optional[sessionmaker] = None
        
        self._last_check: datetime = datetime.min
        self._reconnect_interval = timedelta(minutes=30)
        self._reconnect_state = False

    # Добавление таймера на переподключение
    async def add_timer_reconnect(self, interval: int = 30, state: bool = False) -> bool:
        if state:
            self._reconnect_interval = timedelta(minutes=interval)
            self._reconnect_state = True
            return True
        else:
            self._reconnect_state = False
            return False
    
    # Получение настроек клиента
    async def get_settings(self) -> Dict[str, Any]:
        return {
            "connect": {
                "state": self.connected,
                "host": self.host,
                "port": self.port
            },
            "security": {
                "username": self.username,
                "password": self.password,
                "database": self.database
            },
            "timer": {
                "state": self._reconnect_state,
                "interval": self._reconnect_interval.seconds // 60,
                "check": self._last_check
            }  
        }            
    
    # Подключение к СУБД
    async def connect(self) -> bool:
        try:

            # Преобразование пароля
            quoted_password = quote_plus(self.password)

            # Формирование строки подключения в зависимости от типа СУБД
            url = f"postgresql+asyncpg://{self.username}:{quoted_password}@{self.host}:{self.port}/{self.database}"

            # Инициализация асинхронного движка SQLAlchemy
            self.engine = create_async_engine(url, echo=False, pool_pre_ping=True)

            # Тест запроса на подключение
            async with self.engine.connect() as conn:
                _ = await conn.execute(text("SELECT 1"))

            # Создание асинхронной сессии
            self.async_session = sessionmaker(self.engine, expire_on_commit=False, class_=AsyncSession) #type: ignore
            self.connected = True
            self._last_check = datetime.now()

            return True
        except Exception as e:
            await self.handle_error(e)
            self.connected = False
            return False

    # Отключение от БД
    async def disconnect(self) -> bool:
        try:
            # Проверка активного соединения
            if self.connected:
                self._last_check = datetime.now()

                # Проверка активной сессии
                # Закрываем двигатель, что приведет к закрытию всех активных сессий
                if self.engine:
                    await self.engine.dispose()
                    self.engine = None
                    self.connected = False

                    print(f"Disconnected from {self.host}:{self.port}")
                    return True
            return True
        except Exception as e:
            await self.handle_error(e)
            return False

    # Проверка подключения или переподключение при истечении таймера
    async def connect_state(self) -> bool:
        if not self.connected:
            await self.connect()
        
        if self._reconnect_state and datetime.now() - self._last_check > self._reconnect_interval:
            await self.connect()
            
        return self.connected

    # Создание таблицы модели, если она ещё не существует
    async def create_table_if_not_exists(self, model: Type) -> bool:
        if not await self.connect_state():
            return False
        try:
            async with self.engine.begin() as conn: #type: ignore
                await conn.run_sync(lambda sync_conn: model.__table__.create(bind=sync_conn, checkfirst=True))
            return True
        except Exception as e:
            await self.handle_error(e)
            return False

    # Выборка моделей из БД с фильтрацией (ORM)
    async def select_model(self, model: Type, *filters: Any, filter_by: Optional[Dict[str, Any]] = None, fetch_many: bool = False) -> Optional[Any] | List[Any] | None:
        if not await self.connect_state():
            return None

        try:
            async with self.async_session() as session: #type: ignore
                # Генерация фильтров
                stmt = await self.add_filters(model, *filters, filter_by=filter_by)

                # Получение записи на основе фильтров
                result = await session.execute(stmt)
                items = result.scalars()
        
                return items.all() if fetch_many else items.first()
        except Exception as e:
            await self.handle_error(e)
            return None

    # Вставка записи по переданным полям
    async def insert_model(self, model: Type, data: List[dict], fetch_many: bool = False) -> Optional[Any] | List[Any]:
        # Если Бд - не подключена
        if not await self.connect_state():
            return None

        try:
            async with self.async_session() as session: #type: ignore
                if fetch_many:
                    result = []
                    for item in data:
                        instance = model(**item)
                        session.add(instance)
                        await session.commit()
                        await session.refresh(instance)  # Обновляем данные из БД
                        result.append(instance)
                    return result
                else:
                    instance = model(**data[0])
                    session.add(instance)
                    await session.commit()
                    await session.refresh(instance)  # Обновляем данные из БД
                    return instance
        except Exception as e:
            await self.handle_error(e)
            return None

    # Функция частичного обновления записи
    async def update_record_partition(self, model: Type, *filters: Any, new_data: Dict[str, Any], filter_by: Optional[Dict[str, Any]] = None, fetch_many: bool = False) -> Optional[Any] | List[Any] | None:
        if not await self.connect_state():
            return None

        try:
            async with self.async_session() as session:  # type: ignore
                # Генерация фильтров
                stmt = await self.add_filters(model, *filters, filter_by=filter_by)

                # Запрашиваем нужные записи
                result = await session.execute(stmt)
                instances = result.scalars().all()  # Все записи, подходящие под фильтр

                # Массив обновленных экземпляров
                updated_instances = []

                # Применяем новые данные ко всем экземплярам
                for i, instance in enumerate(instances):
                    # Обновляем только первые найденные, если нужен единичный вариант
                    if not fetch_many and i > 0:
                        break

                    # Обновляем атрибуты записи новыми значениями
                    for key, value in new_data.items():
                        if hasattr(instance, key):
                            setattr(instance, key, value)

                    updated_instances.append(instance)

                # Сохраняем изменения
                await session.commit()
                for instance in updated_instances:
                    await session.refresh(instance)  # Обновляем состояние модели из базы

                # Возвращаем результаты в зависимости от флага
                if fetch_many:
                    return updated_instances
                else:
                    return updated_instances[0] if updated_instances else None

        except Exception as e:
            await self.handle_error(e)
            return None
        
    # Удаление записи по фильтрам
    async def delete_record(self, model: Type, *filters: Any, filter_by: Optional[Dict[str, Any]] = None, fetch_many: bool = False) -> Optional[Any] | List[Any] | None:
        if not await self.connect_state():
            return None

        try:
            async with self.async_session() as session:  # type: ignore
                # Генерация фильтров
                stmt = await self.add_filters(model, *filters, filter_by=filter_by)

                # Получение записей на основе фильтров
                result = await session.execute(stmt)
                instances = result.scalars().all()  # Все записи, подходящие под фильтр

                deleted_instances = []  # Будущие удалённые записи

                # Проходим по каждой записи
                for i, instance in enumerate(instances):
                    # Только первую запись, если единичное удаление
                    if not fetch_many and i > 0:
                        break

                    # Удаляем экземпляр
                    await session.delete(instance)
                    deleted_instances.append(instance)

                # Сохраняем изменения
                await session.commit()

                # Возвращаем результат в зависимости от параметра fetch_many
                if fetch_many:
                    return deleted_instances
                else:
                    return deleted_instances[0] if deleted_instances else None

        except Exception as e:
            await self.handle_error(e)
            return None
        
    # Выполнение произвольного SQL-запроса
    async def manual_execute(self, query: str, params: Optional[Union[Dict[str, Any], tuple]] = None, response: bool = True, fetch_many: bool = False) -> List[Dict[str, Any]] | Dict[str, Any] | None:
        if not await self.connect_state():
            return None

        try:
            # Открытие сессии и выполнение запроса
            async with self.async_session() as session:  # type: ignore
                async with session.begin():  # Начинаем транзакцию
                    result = await session.execute(text(query), params)

                    # Если результат не возвращает строки (например, INSERT, UPDATE, DELETE),
                    # проверяем наличие ключа 'rowcount', который доступен для некоторых запросов
                    if not response:
                        return None

                    # Иначе пытаемся собрать результат, если запрос возвращает строки
                    keys = result.keys()
                    rows = [dict(zip(keys, row)) for row in result]

                    # Возвращаем результат в зависимости от параметра fetch_many
                    return (rows[0] if rows else None) if not fetch_many else (rows if rows else None)

        except Exception as e:
            await self.handle_error(e)
            return None

    # Обработка и вывод ошибок
    @staticmethod
    async def handle_error(error: Exception) -> None:
        print(error)

    # Применение фильтров
    @staticmethod
    async def add_filters(model: Type, *filters: Any, filter_by: Optional[Dict[str, Any]] = None) -> None:
        stmt = select(model)

        # Объединяем два варианта фильтрации в одном условии
        if filters or filter_by:
            if filters:
                stmt = stmt.where(*filters)
            if filter_by:
                stmt = stmt.filter_by(**filter_by)

        return stmt #type: ignore
