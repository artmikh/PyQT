import argparse
import json
import logging
from descriptor import Port
import select
import sys
import threading
# from socket import socket, AF_INET, SOCK_STREAM
import socket
import time
import logs.configuration_server
from utils.decorators import log
from utils.utils import load_configs, get_message, send_message
from metaclasses import ServerMaker
from server_base import ServerStorage
from PyQt5.QtWidgets import QApplication, QMessageBox
from PyQt5.QtCore import QTimer
from server_gui import MainWindow, gui_create_model, HistoryWindow, create_stat_model, ConfigWindow
from PyQt5.QtGui import QStandardItemModel, QStandardItem
import os


CONFIGS = dict()
CONFIGS = load_configs()

# Инициализация логирования сервера.
SERVER_LOGGER = logging.getLogger('server')

# Флаг что был подключён новый пользователь, нужен чтобы не мучать BD
# постоянными запросами на обновление
new_connection = False
conflag_lock = threading.Lock()

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
class Server(threading.Thread, metaclass=ServerMaker):
       
    port = Port()
    
    def __init__(self, listen_address, listen_port, database):
        # Параментры подключения
        self.addr = listen_address
        self.port = listen_port

        # База данных сервера
        self.database = database

        # Список подключённых клиентов.
        self.clients = []

        # Список сообщений на отправку.
        self.messages = []

        # Словарь содержащий сопоставленные имена и соответствующие им сокеты.
        self.names = dict()

        # Конструктор предка
        super().__init__()
        
    
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
                self.client, self.client_address = self.sock.accept()
            except OSError:
                pass
            else:
                SERVER_LOGGER.info(f'Установлено соедение с ПК {self.client_address}')
                self.clients.append(self.client)
                # print(f'client = {client}; client_address = {client_address}')
                # print(f'clients = {self.clients}')
                # print(self.clients.client_address[0])
                # print(self.sock)

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
        global new_connection
        SERVER_LOGGER.debug(f'Обработка сообщения от клиента : {message}')
        if CONFIGS.get('ACTION') in message \
                and message[CONFIGS.get('ACTION')] == CONFIGS.get('PRESENCE') \
                and CONFIGS.get('TIME') in message \
                and CONFIGS.get('USER') in message:
            self.database.user_login(message[CONFIGS.get('USER')][CONFIGS.get('ACCOUNT_NAME')], self.client_address[0], self.client_address[1])
            with conflag_lock:
                    new_connection = True
            return {CONFIGS.get('RESPONSE'): 200,
                    CONFIGS.get('USER'): message[CONFIGS.get('USER')][CONFIGS.get('ACCOUNT_NAME')]}
                    
        # Если это сообщение, то добавляем его в очередь сообщений. Ответ не
        # требуется.
        elif CONFIGS.get('ACTION') in message \
                and message[CONFIGS.get('ACTION')] == CONFIGS.get('MESSAGE') \
                and CONFIGS.get('DESTINATION') in message \
                and CONFIGS.get('TIME') in message \
                and CONFIGS.get('SENDER') in message \
                and CONFIGS.get('MESSAGE_TEXT') in message \
                and self.names[message[CONFIGS.get('SENDER')]] == CONFIGS.get('USER'): #self.client
            self.messages.append(message)
            self.database.process_message(
                message[CONFIGS.get('SENDER')], message[CONFIGS.get('DESTINATION')])
            return

        # Если клиент выходит
        elif CONFIGS.get('ACTION') in message \
                and message[CONFIGS.get('ACTION')] == 'exit' \
                and CONFIGS.get('ACCOUNT_NAME') in message:
            self.database.user_logout(message[CONFIGS.get('ACCOUNT_NAME')])
            self.clients.remove(self.names[message[CONFIGS.get('ACCOUNT_NAME')]])
            self.names[message[CONFIGS.get('ACCOUNT_NAME')]].close()
            del self.names[message[CONFIGS.get('ACCOUNT_NAME')]]
            with conflag_lock:
                new_connection = True
            return

        # Если это запрос контакт-листа
        elif CONFIGS.get('ACTION') in message \
                and message[CONFIGS.get('ACTION')] == CONFIGS.get('GET_CONTACTS') \
                and CONFIGS.get('USER') in message \
                and self.names[message[CONFIGS.get('USER')]] == CONFIGS.get('USER'): #self.client
            response = {CONFIGS.get('RESPONSE'): 200},
            response[CONFIGS.get('LIST_INFO')] = self.database.get_contacts(message[CONFIGS.get('USER')])
            send_message(self.client, response)

        # Если это добавление контакта
        elif CONFIGS.get('ACTION') in message and message[CONFIGS.get('ACTION')] == CONFIGS.get('ADD_CONTACT') and CONFIGS.get('ACCOUNT_NAME') in message and CONFIGS.get('USER') in message \
                and self.names[message[CONFIGS.get('USER')]] == self.client:
            self.database.add_contact(message[CONFIGS.get('USER')], message[CONFIGS.get('ACCOUNT_NAME')])
            send_message(self.client, {CONFIGS.get('RESPONSE'): 200})

        # Если это удаление контакта
        elif CONFIGS.get('ACTION') in message and message[CONFIGS.get('ACTION')] == CONFIGS.get('REMOVE_CONTACT') and CONFIGS.get('ACCOUNT_NAME') in message and CONFIGS.get('USER') in message \
                and self.names[message[CONFIGS.get('USER')]] == self.client:
            self.database.remove_contact(message[CONFIGS.get('USER')], message[CONFIGS.get('ACCOUNT_NAME')])
            send_message(self.client, {CONFIGS.get('RESPONSE'): 200})

        # Если это запрос известных пользователей
        elif CONFIGS.get('ACTION') in message and message[CONFIGS.get('ACTION')] == CONFIGS.get('USERS_REQUEST') and CONFIGS.get('ACCOUNT_NAME') in message \
                and self.names[message[CONFIGS.get('ACCOUNT_NAME')]] == self.client:
            response = {CONFIGS.get('RESPONSE'): 202, CONFIGS.get('LIST_INFO'):None}
            response[CONFIGS.get('LIST_INFO')] = [user[0]
                                   for user in self.database.users_list()]
            send_message(self.client, response)

        # Иначе отдаём Bad request
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

    # Инициализация базы данных
    database = ServerStorage()

    # Создание экземпляра класса - сервера.
    server = Server(listen_address, listen_port, database)
    # server.main_loop()

    # Создаём графическое окуружение для сервера:
    server_app = QApplication(sys.argv)
    main_window = MainWindow()

    # Инициализируем параметры в окна
    main_window.statusBar().showMessage('Server Working')
    main_window.active_clients_table.setModel(gui_create_model(database))
    main_window.active_clients_table.resizeColumnsToContents()
    main_window.active_clients_table.resizeRowsToContents()

    # Функция обновляющяя список подключённых, проверяет флаг подключения, и
    # если надо обновляет список
    def list_update():
        global new_connection
        if new_connection:
            main_window.active_clients_table.setModel(
                gui_create_model(database))
            main_window.active_clients_table.resizeColumnsToContents()
            main_window.active_clients_table.resizeRowsToContents()
            with conflag_lock:
                new_connection = False
    
    # Функция создающяя окно со статистикой клиентов
    def show_statistics():
        global stat_window
        stat_window = HistoryWindow()
        stat_window.history_table.setModel(create_stat_model(database))
        stat_window.history_table.resizeColumnsToContents()
        stat_window.history_table.resizeRowsToContents()
        stat_window.show()

    # Функция создающяя окно с настройками сервера.
    def server_config():
        global config_window
        # Создаём окно и заносим в него текущие параметры
        config_window = ConfigWindow()
        config_window.db_path.insert(CONFIGS.get('DATABASE_PATH'))
        config_window.db_file.insert(CONFIGS.get('DATABASE_FILE'))
        config_window.port.insert(CONFIGS.get('DEFAULT_PORT'))
        config_window.ip.insert(CONFIGS.get('DEFAULT_IP_ADDRESS'))
        config_window.save_btn.clicked.connect(save_server_config)

    # Функция сохранения настроек
    def save_server_config():
        global config_window
        message = QMessageBox()
        CONFIGS['DATABASE_PATH'] = config_window.db_path.text()
        CONFIGS['DATABASE_FILE'] = config_window.db_file.text()
        try:
            port = int(config_window.port.text())
        except ValueError:
            message.warning(config_window, 'Ошибка', 'Порт должен быть числом')
        else:
            listen_address = config_window.ip.text()
            if 1023 < port < 65536:
                listen_port = str(port)
                print(port)
                # with open('server.ini', 'w') as conf:
                #     CONFIGS.write(conf)
                #     message.information(
                #         config_window, 'OK', 'Настройки успешно сохранены!')
            else:
                message.warning(
                    config_window,
                    'Ошибка',
                    'Порт должен быть от 1024 до 65536')

    # Таймер, обновляющий список клиентов 1 раз в секунду
    timer = QTimer()
    timer.timeout.connect(list_update)
    timer.start(1000)

    # Связываем кнопки с процедурами
    main_window.refresh_button.triggered.connect(list_update)
    main_window.show_history_button.triggered.connect(show_statistics)
    main_window.config_btn.triggered.connect(server_config)

    
    # server.main_loop()
    main_window.show()
    # server.main_loop()
    # Запускаем GUI
    # server_app.exec_()
    sys.exit(server_app.exec_())

    
    # # Создание экземпляра класса - сервера.
    # server = Server(listen_address, listen_port, database)
    server.main_loop()
    


if __name__ == '__main__':
    main()
