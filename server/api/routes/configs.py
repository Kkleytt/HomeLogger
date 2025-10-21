from fastapi import APIRouter, HTTPException
from pydantic import ValidationError



from server.config.schema import ServerConfig
from server.config.config import ConfigManager as cfg

router = APIRouter()

@router.get("/config", response_model=ServerConfig)
async def get_current_config():
    return cfg.config

@router.put("/config", response_model=ServerConfig)
async def update_config(new_config: dict):
    try:
        validation_data = ServerConfig(**new_config)
        await cfg.update_config(new_config_data=new_config)
        return validation_data
    
    except ValidationError as e:
        print(f"Error validating new config: {e}")
        return HTTPException(status_code=400, detail="Error validation new config")
    
    except Exception as e:
        print(f"Error updating config: {e}")
        return HTTPException(status_code=500, detail="Internal Server Error")