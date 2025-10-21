# app/server/wiki/wiki_config.py
# Модуль с описанием как работать с конфигурацией проекта

from server.config.config import ConfigManager as cfg

def random_function(host, port, username, password, queue):
    print(f"Параметры функции: {host}, {port}, {username}, {password}, {queue}")
    
def random_function_2(**kwargs):
    for key, value in kwargs.items():
        print(f"{key}: {value}")


def main():
    # Пример получения всех параметров в формате JSON
    print(cfg.config)
    
    # Пример получения класса параметров в формате JSON
    print(cfg.config.rabbitmq)
    
    # Пример получения конкретного параметра из класса
    print(cfg.config.rabbitmq.host)
    
    # Пример передачи раскрывающегося списка параметров
    random_function(*cfg.config.rabbitmq)
    
    # Пример передачи рандомных параметров в функцию
    random_function_2(*cfg.config.timescaledb)


if __name__ == "__main__":
    main()