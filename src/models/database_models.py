from sqlalchemy import Column, Integer, String, Text, DateTime, Index
from sqlalchemy.orm import declarative_base
from datetime import datetime, timezone

Base = declarative_base()

def generate_log_model(table_name: str = "unknown"):
    """ Функция для генерации SqlAlchemy модели таблицы логов

    Arguments:
        table_name {str} -- Имя таблицы

    Returns:
        _type_ -- declarative_base() -- Возвращает модель таблицы логов
    """
    
    class DynamicLogRecord(Base):
        __tablename__ = table_name

        # Первичный ключ
        id = Column(Integer, primary_key=True, autoincrement=True, nullable=False, index=True)

        # Уровень лога ["info", "warning", "error", "fatal", "debug", "alert", "unknown"]
        level = Column(String(7), nullable=False, index=True)

        # Timestamp формата ISO 8601 ["2024-01-01T00:00:00Z"]
        timestamp = Column(DateTime(timezone=True), default=datetime.now(timezone.utc), nullable=False, index=True)

        # Модуль, который записал лог
        module = Column(String(50), nullable=True)

        # Функция, которая записала лог
        function = Column(String(50), nullable=True)

        # Сообщение лога
        message = Column(Text, nullable=False)

        # Код ошибки, если есть
        code = Column(Integer, nullable=False, server_default="0", index=True)

        # Индексация для повышения производительности
        __table_args__ = (
            Index(f'{table_name}_level_timestamp_idx', 'level', 'timestamp'),
            Index(f'{table_name}_module_function_idx', 'module', 'function'),
        )

        def __repr__(self):
            return f"<DynamicLogRecord({self.id}, {self.level}, {self.timestamp})>"

    return DynamicLogRecord if table_name != "unknown" else None


# Пример использования
if __name__ == "__main__":
    AirborneModel = generate_log_model("airborne")
    print(AirborneModel)