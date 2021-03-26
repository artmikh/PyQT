import argparse
import json
import logging
import sys
from socket import socket, AF_INET, SOCK_STREAM
import threading
import time
from typing import Text
import logs.configuration_client
from utils.decorators import Log
from utils.utils import load_configs, send_message, get_message

CONFIGS = dict()
CONFIGS = load_configs(is_server=False)
SERVER_LOGGER = logging.getLogger('client')

SEMAPHOR = threading.Semaphore(1)


# добавка
@Log()
def create_exit_message(account_name):
    return {
        CONFIGS['ACTION']: CONFIGS['EXIT'],
        CONFIGS['TIME']: time.time(),
        CONFIGS['ACCOUNT_NAME']: account_name
    }

@Log()
def create_presence_message(CONFIGS, account_name='Guest'):
    message = {
        CONFIGS.get('ACTION'): CONFIGS.get('PRESENCE'),
        CONFIGS.get('TIME'): time.time(),
        CONFIGS.get('USER'): {
            CONFIGS.get('ACCOUNT_NAME'): account_name
        }
    }
    SERVER_LOGGER.info('Создание сообщения для отпарвки на сервер.')
    return message


# добавка
def create_message(sock, account_name='Guest'):
    while True:
        print(f'def create_message {account_name}')
        to_user = input('Введите получателя сообщения: ')
        if to_user =='exit':
            break
        message = input('Введите сообщение для отправки: ')
        if message =='exit':
            break
        message_dict = {
            CONFIGS['ACTION']: CONFIGS['MESSAGE'],
            CONFIGS['SENDER']: account_name,
            CONFIGS['DESTINATION']: to_user,
            CONFIGS['TIME']: time.time(),
            CONFIGS['MESSAGE_TEXT']: message
        }
        # print(message_dict)
        # print(CONFIGS)
        SERVER_LOGGER.debug(f'Сформирован словарь сообщения: {message_dict}')
        try:
            send_message(sock, message_dict, CONFIGS)
            SERVER_LOGGER.info(f'Отправлено сообщение для пользователя {to_user}')
            print(f'Отправлено сообщение для пользователя {to_user}')
        except:
            SERVER_LOGGER.critical('Потеряно соединение с сервером.1')
            sys.exit(1)

def create_message_for_all(sock, account_name='Guest'):
    message = input('Введите сообщение для отправки: ')
    message_dict = {
            CONFIGS['ACTION']: CONFIGS['MESSAGE'],
            CONFIGS['SENDER']: account_name,
            CONFIGS['TIME']: time.time(),
            CONFIGS['MESSAGE_TEXT']: message
        }
    SERVER_LOGGER.debug(f'Сформирован словарь сообщения: {message_dict}')
    try:
        send_message(sock, message_dict, CONFIGS)
        SERVER_LOGGER.info(f'Отправлено сообщение')
        print(f'(Отправлено сообщение)')
    except:
        SERVER_LOGGER.critical('Потеряно соединение с сервером.2')
        sys.exit(1)

@Log()
def arg_parser(CONFIGS):
    parser = argparse.ArgumentParser()
    parser.add_argument('addr', default=CONFIGS['DEFAULT_IP_ADDRESS'], nargs='?')
    parser.add_argument('port', default=CONFIGS['DEFAULT_PORT'], type=int, nargs='?')
    parser.add_argument('-m', '--mode', default='listen', nargs='?')
    parser.add_argument('-n', '--name', default='Guest', nargs='?')
    namespace = parser.parse_args(sys.argv[1:])
    server_address = namespace.addr
    server_port = namespace.port
    client_mode = namespace.mode
    account_name = namespace.name

    if not 1023 < server_port < 65536:
        SERVER_LOGGER.critical('Порт должен быть указан в пределах от 1024 до 65535')
        sys.exit(1)

    if client_mode not in ('listen', 'send'):
        SERVER_LOGGER.critical(f'Указан недопустимый режим работы {client_mode}, допустимые режимы: listen , send')
        sys.exit(1)

    return server_address, server_port, client_mode, account_name


@Log()
def handle_response(message, CONFIGS):
    print('Обработка сообщения от сервера.')
    SERVER_LOGGER.info('Обработка сообщения от сервера.')
    if CONFIGS.get('RESPONSE') in message:
        if message[CONFIGS.get('RESPONSE')] == 200:
            SERVER_LOGGER.info('Успешная обработка сообшения от сервера.')
            return '200 : OK'
        SERVER_LOGGER.critical('Обработка сообщения от сервера провалилась.')
        return f'400 : {message[CONFIGS.get("ERROR")]}'
    # raise ValueError

# добавка
@Log()
def message_from_server(sock, account_name):
    while True:
        try:
            SEMAPHOR.release()
            # print('ждем')
            message = get_message(sock, CONFIGS)
            if CONFIGS['ACTION'] in message \
                and message[CONFIGS['ACTION']] == CONFIGS['MESSAGE'] \
                and CONFIGS['SENDER'] in message \
                and message[CONFIGS["SENDER"]] != account_name \
                and CONFIGS['MESSAGE_TEXT'] in message:
                # and CONFIGS['DESTINATION'] in message \
                # and message[CONFIGS['DESTINATION']] == account_name:
                print(f'\nПолучено сообщение от пользователя {message[CONFIGS["SENDER"]]}:'
                      f'\n{message[CONFIGS["MESSAGE_TEXT"]]}')
                SERVER_LOGGER.info(f'Получено сообщение от пользователя {message[CONFIGS["SENDER"]]}:'
                            f'\n{message[CONFIGS["MESSAGE_TEXT"]]}')
            # else:
            #     print('->')
            # print('прошел цикл')
            # else:
            #     SERVER_LOGGER.error(f'Получено некорректное сообщение с сервера: {message}')
        # except IncorrectDataRecivedError:
        #     SERVER_LOGGER.error(f'Не удалось декодировать полученное сообщение.')
        except (OSError, ConnectionError, ConnectionAbortedError,
                ConnectionResetError, json.JSONDecodeError):
            SERVER_LOGGER.critical(f'Потеряно соединение с сервером.3')
            break

# добавка
# def user_interactive(sock, username):
#     # print(help_text())
#     while True:
#         command = input('Введите команду: ')
#         if command == 'message':
#             create_message(sock, username)
#         # elif command == 'help':
#         #     print(help_text())
#         elif command == 'exit':
#             send_message(sock, create_exit_message(username), CONFIGS)
#             print('Завершение соединения.')
#             SERVER_LOGGER.info('Завершение работы по команде пользователя.')
#             time.sleep(0.5)
#             break
#         else:
#             print('Команда не распознана, попробойте снова. help - вывести поддерживаемые команды.')
#         SEMAPHOR.release()

def user_text(sock, username):
    while True:
        SEMAPHOR.acquire()
        # print('отпустили семафор')
        # create_message(sock, username)
        create_message_for_all(sock, username)
        

def main():
    # if not account_name:
    #     account_name = input("Your name: ")

    global CONFIGS
    # CONFIGS = load_configs(is_server=False)
    server_address, server_port, client_mode, account_name = arg_parser(CONFIGS)
    print(client_mode)
    try:
        transport = socket(AF_INET, SOCK_STREAM)
        transport.connect((server_address, server_port))
        print(f'1-> {transport}')
        presence_message = create_presence_message(CONFIGS, account_name)
        print(f'2-> {presence_message}')
        send_message(transport, presence_message, CONFIGS)
        print(f'3-> {server_port}, {server_address}')

        answer = handle_response(get_message(transport, CONFIGS), CONFIGS)
        print(f'4-> {answer}')
        SERVER_LOGGER.info(f'Установлено соединение с сервером. Ответ сервера: {answer}')
        print(f'Установлено соединение с сервером. Ответ сервера: {answer}')
    except json.JSONDecodeError:
        SERVER_LOGGER.error('Не удалось декодировать полученную Json строку.')
        sys.exit(1)
    
    except ConnectionRefusedError:
        SERVER_LOGGER.critical(
            f'Не удалось подключиться к серверу {server_address}:{server_port}, '
            f'конечный компьютер отверг запрос на подключение.')
        sys.exit(1)

    else:
        # account_name = ''
        
        receiver = threading.Thread(target=message_from_server, args=(transport, account_name))
        user_interface = threading.Thread(target=user_text, args=(transport, account_name))
        
        receiver.daemon = True
        user_interface.daemon = True
        
        receiver.start()
        user_interface.start()
        
        receiver.join()
        user_interface.join()

        SERVER_LOGGER.debug('Запущены процессы')

if __name__ == '__main__':
    main()
