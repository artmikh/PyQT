import argparse
import json
import logging
import select
import sys
from socket import socket, AF_INET, SOCK_STREAM
import time
import messenger.logs.configuration_server
from messenger.utils.decorators import log
from messenger.utils.utils import load_configs, get_message, send_message

CONFIGS = dict()

SERVER_LOGGER = logging.getLogger('server')

@log
def handle_message(message, CONFIGS):  # функция проверки presense сообщения от клиента
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

def arg_parser(CONFIGS):
    global SERVER_LOGGER
    parser = argparse.ArgumentParser()
    parser.add_argument('-p', default=CONFIGS['DEFAULT_PORT'], type=int, nargs='?')
    parser.add_argument('-a', default='', nargs='?')
    namespace = parser.parse_args(sys.argv[1:])
    listen_address = namespace.a
    listen_port = namespace.p

    if not 1023 < listen_port < 65536:
        SERVER_LOGGER.critical(f'Попытка запуска сервера с некорректного порта {listen_port}.'
                               'Порт должен быть указан в пределах от 1024 до 65535')
        sys.exit(1)

    return listen_address, listen_port

def read_request(r_list, clients):
    responses = {}

    for sock in r_list:
        try:
            data = get_message(sock, CONFIGS)
            responses[sock] = data
        except:
            clients.remove(sock)
    return responses

def write_responses(requests, w_list, clients):
    for sock in w_list:
        for _, request in requests.items():  
            if request['action'] == 'presence':
                req_pres = handle_message(request, CONFIGS)
                send_message(sock, req_pres, CONFIGS)
            else:
                try:
                    send_message(sock, request, CONFIGS)
                except:
                    sock.close()
                    clients.remove(sock)

def main():
    global CONFIGS, SERVER_LOGGER
    CONFIGS = load_configs()
    listen_address, listen_port = arg_parser(CONFIGS)
    SERVER_LOGGER.info(f'Сервер запущен на порту: {listen_port}, по адресу: {listen_address}.')

    transport = socket(AF_INET, SOCK_STREAM)
    transport.bind((listen_address, listen_port))
    transport.settimeout(0.5)

    transport.listen(CONFIGS.get('MAX_CONNECTIONS'))
    clients = []
    messages = []

    while True:
        try:
            client, client_address = transport.accept()
        except OSError:
            pass
        else:
            SERVER_LOGGER.info(f'Установлено соедение с ПК {client_address}')
            clients.append(client)

        recv_data_lst = []
        send_data_lst = []
        err_lst = []
        try:
            if clients:
                recv_data_lst, send_data_lst, err_lst = select.select(clients, clients, [], 0)
        except OSError:
            pass

        requests = read_request(recv_data_lst, clients)
        # print(f'Прочитаны сообщения {requests}')
        if requests:
            write_responses(requests, send_data_lst, clients)
            print(f'Отправлены сообщения ')

if __name__ == '__main__':
    main()
