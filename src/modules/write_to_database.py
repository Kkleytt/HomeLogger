# app/src/modules/write_to_database.py
# Модуль для записи логов в базу данных

from src.databases.postgres_client import LogClient
from src.models.database_models import generate_log_model
from src.config import CurrentConfig as cfg

from datetime import datetime


sql_client = LogClient(**cfg.timescaledb)

database_models = {}

async def write_to_database(log_message: dict) -> bool | int:
    
    project = log_message["project"]
    
    if project not in database_models:
        database_models[project] = generate_log_model(project)
    
    return await sql_client.insert_log(
        model=database_models[project],
        log={
            "level": log_message["level"],
            "timestamp": datetime.fromisoformat(log_message["timestamp"]),
            "module": log_message["module"],
            "function": log_message["function"],
            "message": log_message["message"],
            "code": log_message["code"]
        }
    )