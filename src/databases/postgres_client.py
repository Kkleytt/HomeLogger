# app/src/databases/postgres_client.py
# Модуль для работы с PostgreSQL / TimeScaleDB

from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Type, Union
from urllib.parse import quote_plus

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.sql import text

from src.models.config_models import ServerConfig


class Client:
    def __init__(self, config: ServerConfig.TimescaleDB) -> None:
        # Установка значений переменных
        self.host = config.host
        self.port = config.port
        self.username = config.username
        self.password = config.password
        self.database = config.database

        # Служебные переменные
        self.connected = False
        self.engine = None
        self.async_session: Optional[sessionmaker] = None
        
        self._last_check: datetime = datetime.min
        self._reconnect_interval = timedelta(minutes=30)
        self._reconnect_state = False

    # Добавление таймера на переподключение
    async def add_timer_reconnect(self, interval: int = 30, state: bool = False) -> bool:
        """ Функция для добавления таймера на переподключение к базе данных

        Keyword Arguments:
            interval {int} -- Интервал таймера в минутах (default: {30})
            state {bool} -- Статус таймера (default: {False})

        Returns:
            bool -- Статуса добавления таймера
        """
        
        if state:
            self._reconnect_interval = timedelta(minutes=interval)
            self._reconnect_state = True
            return True
        else:
            self._reconnect_state = False
            return False
    
    # Получение настроек клиента
    async def get_settings(self) -> Dict[str, Any]:
        """Функция для получения настроек клиента

        Returns:
            Dict[str, Any] -- Словарь с настройками клиента
        """
        
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
        """ Функция для подключения к СУБД

        Returns:
            bool -- Статус подключения
        """
        
        try:

            # Преобразование пароля
            quoted_password = quote_plus(self.password) #type: ignore

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
        """ Функция для отключения от БД

        Returns:
            bool -- Статус отключения
        """
        
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
        """ Функция для проверки подключения к БД

        Returns:
            bool -- Статус подключения
        """
        
        if not self.connected:
            await self.connect()
        
        if self._reconnect_state and datetime.now() - self._last_check > self._reconnect_interval:
            await self.connect()
            
        return self.connected

    # Создание таблицы модели, если она ещё не существует
    async def create_table_if_not_exists(self, model: Type) -> bool:
        """ Функция для создания таблицы в БД, если она ещё не существует

        Arguments:
            model {Type} -- Модель для создания таблицы SqlAlchemy

        Returns:
            bool -- Статус создания таблицы
        """
        
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
        """ Функция для выборки моделей из БД с фильтрацией

        Arguments:
            model {Type} -- Модель для выборки SqlAlchemy

        Keyword Arguments:
            filters {Any} -- Фильтры для выборки (default: {None})
            filter_by {Optional[Dict[str, Any]]} -- Фильтры для выборки по полям (default: {None})
            fetch_many {bool} -- Флаг для выборки одной или всех записей (default: {False})

        Returns:
            Optional[Any] | List[Any] | None -- Модель | Список моделей или None (если не нашлось данных или возникла ошибка)
        """
        
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
    async def insert_model(self, model: Type, data: List[dict], fetch_many: bool = False) -> Optional[Any] | List[Any] | None:
        """ Функция для вставки записи в БД

        Arguments:
            model {Type} -- Модель для вставки SqlAlchemy
            data {List[dict]} -- Список словарей с данными для вставки

        Keyword Arguments:
            fetch_many {bool} -- Флаг для выборки одной или всех записей (default: {False})

        Returns:
            Optional[Any] | List[Any] | None -- Модель | Список моделей или None (если не произошла запись или возникла ошибка)
        """
        
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
        """ Функция для частичного обновления записи в БД

        Arguments:
            model {Type} -- Модель для обновления SqlAlchemy
            new_data {Dict[str, Any]} -- Новые данные для обновления

        Keyword Arguments:
            filter_by {Optional[Dict[str, Any]]} -- Фильтры для выборки по полям (default: {None})
            fetch_many {bool} -- Флаг для выборки одной или всех записей (default: {False})

        Returns:
            Optional[Any] | List[Any] | None -- Модель | Список моделей или None (если не произошло обновление записи или возникла ошибка)
        """
        
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
        """ Функция для удаления записи из БД

        Arguments:
            model {Type} -- Модель для удаления SqlAlchemy

        Keyword Arguments:
            filter_by {Optional[Dict[str, Any]]} -- Фильтры для выборки по полям (default: {None})
            fetch_many {bool} -- Флаг для выборки одной или всех записей (default: {False})

        Returns:
            Optional[Any] | List[Any] | None -- Модель | Список моделей или None (если не произошло удаление записи или возникла ошибка)
        """
        
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
        """ Функция для выполнения произвольного SQL-запроса

        Arguments:
            query {str} -- SQL-запрос

        Keyword Arguments:
            params {Optional[Union[Dict[str, Any], tuple]]} -- Параметры запроса (default: {None})
            response {bool} -- Ожидание ответа от БД (default: {True})
            fetch_many {bool} -- Флаг для выборки одной или всех записей (default: {False})

        Returns:
            List[Dict[str, Any]] | Dict[str, Any] | None -- Список словарей | Словарь | None (если произошла ошибка или запрос не вернул данных)
        """
        
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
        """ Обработка и вывод ошибок

        Arguments:
            error {Exception} -- Ошибка
        """
        
        print(error)

    # Применение фильтров
    @staticmethod
    async def add_filters(model: Type, *filters: Any, filter_by: Optional[Dict[str, Any]] = None) -> None:
        """ Функция для применения фильтров

        Arguments:
            model {Type} -- Модель SqlAlchemy

        Keyword Arguments:
            filter_by {Optional[Dict[str, Any]]} -- Фильтрация по полям (default: {None})

        Returns:
            _type_ -- Возвращает объект запроса
        """
        
        stmt = select(model)

        # Объединяем два варианта фильтрации в одном условии
        if filters or filter_by:
            if filters:
                stmt = stmt.where(*filters)
            if filter_by:
                stmt = stmt.filter_by(**filter_by)

        return stmt #type: ignore



class LogClient(Client):
    async def insert_log(self, model: Type, log: dict) -> bool | int:
        """ Функция для вставки лога в базу данных + валидация

        Arguments:
            model {Type} -- Модель SqlAlchemy
            log {dict} -- Словарь с данными лога

        Returns:
            Optional[Any] | None -- Данные записи в БД или None (если произошла ошибка)
        """
        
        try:
            await self.create_table_if_not_exists(model=model)
            result = await self.insert_model(
                model=model, 
                data=[log], 
                fetch_many=False
                )
            return int(result.id) # type: ignore
        except Exception as e:
            print(f"Ошибка при вставке лога: {e}")
            return False
