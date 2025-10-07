from src.config import CurrentConfig as cfg

def random_function(host, port, username, password, queue):
    print(f"Параметры функции: {host}, {port}, {username}, {password}, {queue}")
    
def random_function_2(**kwargs):
    for key, value in kwargs.items():
        print(f"{key}: {value}")


def main():
    # Пример получения всех параметров в формате JSON
    print(cfg.get_all_config())
    
    # Пример получения класса параметров в формате JSON
    print(cfg.rabbitmq)
    
    # Пример получения конкретного параметра из класса
    print(cfg.rabbitmq['host'])
    
    # Пример получения параметров из другого окружения
    from src.config import TestConfig
    print(TestConfig.rabbitmq['host'])
    
    from src.config import ProductionConfig
    print(ProductionConfig.rabbitmq['host'])
    
    # Пример передачи раскрывающегося списка параметров
    random_function(**cfg.rabbitmq)
    
    # Пример передачи рандомных параметров в функцию
    random_function_2(**cfg.timescaledb)


if __name__ == "__main__":
    main()