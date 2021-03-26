import logging
import sys

SERVER_LOGGER = logging.getLogger('server')


class Port:
    def __set__(self, instance, value):

        if not 1023 < value < 65536:
            SERVER_LOGGER.critical(f'Попытка запуска сервера с некорректного порта {value}.'
                                'Порт должен быть указан в пределах от 1024 до 65535')
            sys.exit(1)
        
        instance.__dict__[self.name] = value

    def __set_name__(self, owner, name):
        
        self.name = name

