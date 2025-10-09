# app/src/modules/write_to_database.py
# Модуль для записи логов в базу данных

import asyncio

from src.databases.postgres_client import LogClient
from src.models.database_models import generate_log_model
from src.config import CurrentConfig as cfg


sql = LogClient(**cfg.timescaledb)

async def write_to_database(log_message: dict) -> bool:
    result = await sql.insert_log(
        model=generate_log_model(),
        log=log_message
    )
    
    return True if isinstance(result, dict) else False