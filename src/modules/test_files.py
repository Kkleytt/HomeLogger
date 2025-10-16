from src.models.config_models import ServerConfig
from src.modules.write_to_files import Writer as FileWriter



def test_write_to_files():
    config = {
        "rotation": {
            "trigger": "lines",
            "lines": 1000
        },
        "archive": {
            "enabled": True,
            "count": 2
        }
    }
    client = FileWriter(
        ServerConfig.Files( 
            **config # type: ignore
        )
    )
    
    log_2 = {
        "project": "test_2",
        "timestamp": "2025-01-01T00:00:00",
        "level": "WARNING",
        "module": "test_module_2",
        "function": "test_function_2",
        "message": "Two test message",
        "code": 321
    }
    
    for i in range(2000):
        client.write_log(log_2)
    
    client.close("test_2")
    
if __name__ == "__main__":
    test_write_to_files()