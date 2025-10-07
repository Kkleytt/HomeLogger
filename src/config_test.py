from config import CurrentConfig as cfg

print(cfg.get_dict_config())
print(cfg.rabbitmq['host'])