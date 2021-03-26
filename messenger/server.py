import argparse
import json
import logging
from descriptor import Port
import select
import sys
# from socket import socket, AF_INET, SOCK_STREAM
import socket
import time
import logs.configuration_server
from utils.decorators import log
from utils.utils import load_configs, get_message, send_message
from metaclasses import ServerMaker

CONFIGS = dict()
CONFIGS = load_configs()

# Инициализация логирования сервера.
SERVER_LOGGER = logging.getLogger('server')

# Парсер аргументов коммандной строки.
def arg_parser(CONFIGS):
    global SERVER_LOGGER
    parser = argparse.ArgumentParser()
    parser.add_argument('-p', default=CONFIGS['DEFAULT_PORT'], type=int, nargs='?')
    parser.add_argument('-a', default='', nargs='?')
    namespace = parser.parse_args(sys.argv[1:])
    listen_address = namespace.a
    listen_port = namespace.p

    return listen_address, listen_port

# Основной класс сервера
class Server(metaclass=ServerMaker):
       
    port = Port()
    
    def __init__(self, listen_address, listen_port):
        # Параментры подключения
        self.addr = listen_address
        self.port = listen_port

        # Список подключённых клиентов.
        self.clients = []

        # Список сообщений на отправку.
        self.messages = []

        # Словарь содержащий сопоставленные имена и соответствующие им сокеты.
        # self.names = dict()
        
    
    def init_socket(self):
        SERVER_LOGGER.info(f'Сервер запущен на порту: {self.port}, по адресу: {self.addr}.')

        transport = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        # transport = socket(AF_INET, SOCK_STREAM) # Почему-то, в этом случае метакласс выдает ошибку, AF_INET и SOCK_STREAM попадают в методы, а не в атрибуты
        transport.bind((self.addr, self.port))
        transport.settimeout(0.5)

        self.sock = transport
        self.sock.listen(CONFIGS.get('MAX_CONNECTIONS'))


    def main_loop(self):
        # Инициализация Сокета
        self.init_socket()

        while True:
            try:
                client, client_address = self.sock.accept()
            except OSError:
                pass
            else:
                SERVER_LOGGER.info(f'Установлено соедение с ПК {client_address}')
                self.clients.append(client)

            recv_data_lst = []
            send_data_lst = []
            err_lst = []
            try:
                if self.clients:
                    recv_data_lst, send_data_lst, err_lst = select.select(self.clients, self.clients, [], 0)
            except OSError:
                pass

            requests = self.read_request(recv_data_lst, self.clients)
            # print(f'Прочитаны сообщения {requests}')
            if requests:
                self.write_responses(requests, send_data_lst, self.clients)
                print(f'Отправлены сообщения ')

    @log
    def handle_message(self, message, CONFIGS):  # функция проверки presense сообщения от клиента
        # print(message[CONFIGS.get('USER')][CONFIGS.get('ACCOUNT_NAME')])
        global SERVER_LOGGER
        SERVER_LOGGER.debug(f'Обработка сообщения от клиента : {message}')
        if CONFIGS.get('ACTION') in message \
                and message[CONFIGS.get('ACTION')] == CONFIGS.get('PRESENCE') \
                and CONFIGS.get('TIME') in message \
                and CONFIGS.get('USER') in message:
            # == message[CONFIGS.get('USER')][CONFIGS.get('ACCOUNT_NAME')]:
            return {CONFIGS.get('RESPONSE'): 200,
                    CONFIGS.get('USER'): message[CONFIGS.get('USER')][CONFIGS.get('ACCOUNT_NAME')]}
        return {
            CONFIGS.get('RESPONSE'): 400,
            CONFIGS.get('ERROR'): 'Bad Request'
        }

    def read_request(self, r_list, clients):
        responses = {}

        for sock in r_list:
            try:
                data = get_message(sock, CONFIGS)
                responses[sock] = data
            except:
                clients.remove(sock)
        return responses

    def write_responses(self, requests, w_list, clients):
        for sock in w_list:
            for _, request in requests.items():  
                if request['action'] == 'presence':
                    req_pres = self.handle_message(request, CONFIGS)
                    send_message(sock, req_pres, CONFIGS)
                else:
                    try:
                        send_message(sock, request, CONFIGS)
                    except:
                        sock.close()
                        clients.remove(sock)

def main():
    # Загрузка параметров командной строки, если нет параметров, то задаём значения по умоланию.
    listen_address, listen_port = arg_parser(CONFIGS)

    # Создание экземпляра класса - сервера.
    server = Server(listen_address, listen_port)
    server.main_loop()

if __name__ == '__main__':
    main()
