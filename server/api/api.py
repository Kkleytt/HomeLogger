from fastapi import FastAPI
import uvicorn

from server.config.config import ConfigManager as cfg
from server.api.routes import config, logs, health


def fastapi_app():
    app = FastAPI(
        title="Logger API",
        description="API для управления логами и настройками",
        version="0.1.0"
    )

    # Подключаем маршруты
    # app.include_router(logs.router, prefix="/api/v1", tags=["logs"])
    app.include_router(config.router, prefix="/api/v1", tags=["config"])
    app.include_router(health.router, prefix="/api/v1", tags=["health"])

    return app


if __name__ == "__main__":
    uvicorn.run(fastapi_app(), host="0.0.0.0", port=8000)