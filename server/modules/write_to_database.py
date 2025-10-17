# app/server/modules/write_to_database.py
# Модуль для записи логов в базу данных

from server.databases.postgres_client import LogClient
from server.models.config_models import ServerConfig
from server.models.database_models import generate_log_model
from datetime import datetime

database_models = {}

    
class Writer:
    def __init__(self, config: ServerConfig.TimescaleDB):
        self.config: ServerConfig.TimescaleDB = config
        self.connect = None
        self.client: LogClient
        
        if not self.connect:
            self._connect()
        
    def _connect(self):
        if self.config.enabled:
            
            self.client = LogClient(self.config)
            
    async def write_log(self, log: dict):
        
        # Проверка на наличие модели БД
        if log["project"] not in database_models:
            database_models[log["project"]] = generate_log_model(log["project"])
            
        return await self.client.insert_log(
            model=database_models[log["project"]],
            log={
                "level": log["level"],
                "timestamp": datetime.fromisoformat(log["timestamp"]),
                "module": log["module"],
                "function": log["function"],
                "message": log["message"],
                "code": log["code"]
            }
        )
        