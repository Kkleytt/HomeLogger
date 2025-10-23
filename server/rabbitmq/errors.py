class ExceptionRabbitMQ():
    class ModuleError(Exception):
        pass
    
    class ConnectionError(Exception):
        pass

    class ConfigError(Exception):
        pass

    class ConfigUpdateError(Exception):
        pass

    class ValidationError(Exception):
        pass

    class StartError(Exception):
        pass

    class StopError(Exception):
        pass

    class UnknownError(Exception):
        pass