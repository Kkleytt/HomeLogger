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
            self.async_session = sessionmaker(self.engine, expire_on_commit=False, class_=AsyncSession)
            self.connected = True
            self._last_check = datetime.now()

            print(f"Connected to {self.host}:{self.port}")

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
                if self.async_session:
                    # Закрытие всех сессий
                    self.async_session.close_all()
                    self.async_session = None
                    self.connected = False

                    print(f"Disconnected from {self.host}:{self.port}")
                    return True
            return True
        except Exception as e:
            await self.handle_error(e)
            return False

    # Проверка подключения или переподключение при истечении таймера
    async def is_connected(self) -> bool:
        if not self.connected or datetime.now() - self._last_check > self._reconnect_interval:
            await self.connect()
        return self.connected

    # Создание таблицы модели, если она ещё не существует
    async def create_table_if_not_exists(self, model: Type) -> bool:
        if not await self.is_connected():
            return False
        try:
            async with self.engine.begin() as conn:
                await conn.run_sync(lambda sync_conn: model.__table__.create(bind=sync_conn, checkfirst=True))
            return True
        except Exception as e:
            await self.handle_error(e)
            return False

    # Выборка моделей из БД с фильтрацией (ORM)
    async def select_model(self, model: Type, *filters: Any, fetch_one: bool = True, filter_by: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]] | Dict[str, Any]:
        if not await self.is_connected():
            return {} if fetch_one else []

        try:
            async with self.async_session() as session:
                # Генерация фильтров
                stmt = await self.add_filters(model, *filters, filter_by=filter_by)

                # Получение записи на основе фильтров
                result = await session.execute(stmt)
                items = result.scalars()

                if fetch_one:
                    instance = items.first()
                    if instance is None:
                        return {} if fetch_one else []
                    
                    return {
                        k: v for k, v in vars(instance).items()
                        if not k.startswith("_")
                    }
                else:
                    instances = items.all()
                    # Преобразуем каждую запись в словарь
                    return [
                        {
                            k: v for k, v in vars(inst).items()
                            if not k.startswith("_")
                        }
                        for inst in instances
                    ]
        except Exception as e:
            await self.handle_error(e)
            return {} if fetch_one else []

    # Вставка записи по переданным полям
    async def insert_model(self, model: Type, data: dict) -> Dict[str, Any]:
        # Если Бд - не подключена
        if not await self.is_connected():
            return {}

        try:
            async with self.async_session() as session:
                instance = model(**data)
                session.add(instance)
                await session.commit()
                await session.refresh(instance)  # Обновляем данные из БД

                # Преобразуем ORM объект в словарь, исключая служебные атрибуты
                return {
                    k: v for k, v in vars(instance).items()
                    if not k.startswith("_")
                }
        except Exception as e:
            await self.handle_error(e)
            return {}

    # Функция частичного обновления записи
    async def update_record_partition(self, model: Type, *filters: Any, new_data: Dict[str, Any], filter_by: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        if not await self.is_connected():
            return {}

        try:
            async with self.async_session() as session:
                # Генерация фильтров
                stmt = await self.add_filters(model, *filters, filter_by=filter_by)

                # Получение записи на основе фильтров
                result = await session.execute(stmt)
                instance = result.scalar_one_or_none()

                if not instance:
                    return {}

                # Обновляем только существующие атрибуты модели
                for key, value in new_data.items():
                    if hasattr(instance, key):
                        setattr(instance, key, value)

                await session.commit()
                await session.refresh(instance)

                # Возврат только публичных данных (без служебных)
                return {
                    key: getattr(instance, key)
                    for key in vars(instance)
                    if not key.startswith("_")
                }

        except Exception as e:
            await self.handle_error(e)
            return {}

    # Удаление записи по фильтрам
    async def delete_record(self, model: Type, *filters: Any, filter_by: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        if not await self.is_connected():
            return {}

        try:
            async with self.async_session() as session:
                # Генерация фильтров
                stmt = await self.add_filters(model, *filters, filter_by=filter_by)

                # Получение записи на основе фильтров
                result = await session.execute(stmt)
                instance = result.scalar_one_or_none()

                # Проверка существования записи + Удаление записи
                if not instance:
                    return {}
                
                await session.delete(instance)
                await session.commit()

                # Преобразуем объект в словарь, исключая служебные атрибуты
                return {
                    k: v for k, v in vars(instance).items()
                    if not k.startswith("_")
                }
        except Exception as e:
            await self.handle_error(e)
            return {}

    # Выполнение произвольного SQL-запроса
    async def manual_execute(self, query: str, params: Optional[Union[Dict[str, Any], tuple]] = None, fetch_one: bool = False) -> List[Dict[str, Any]] | Dict[str, Any]:
        if not await self.is_connected():
            return []

        try:
            # Открытие сессии и выполнение запроса
            async with self.async_session() as session:
                result = await session.execute(text(query), params)
                keys = result.keys()
                rows = [dict(zip(keys, row)) for row in result]

                # Возвращаем либо одну запись, либо все
                return (rows[0] if rows else {}) if fetch_one else (rows if rows else [])
        except Exception as e:
            await self.handle_error(e)
            return []

    # Обработка и вывод ошибок
    @staticmethod
    async def handle_error(error: Exception) -> None:
        print(error)

    # Применение фильтров
    @staticmethod
    async def add_filters(model: Type, *filters: Any, filter_by: Optional[Dict[str, Any]] = None) -> None:
        stmt = select(model)

        if filters is not None:
            stmt = stmt.where(*filters)
        elif filter_by is not None:
            stmt = stmt.filter_by(**filter_by)

        return stmt # type: ignore
