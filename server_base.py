from sqlalchemy import create_engine, Table, Column, Integer, String, MetaData, ForeignKey, DateTime
from sqlalchemy.orm import mapper, sessionmaker
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.sql import base
from utils.utils import load_configs, get_message, send_message
import datetime


CONFIGS = dict()
CONFIGS = load_configs()

# Класс - серверная база данных:
class ServerStorage:
    BASE = declarative_base()
    # Класс - отображение таблицы всех пользователей
    # Экземпляр этого класса = запись в таблице AllUsers
    class AllUsers(BASE):
        # Создаём таблицу пользователей
        __tablename__ = 'Users'
        id = Column(Integer, primary_key=True)
        name = Column(String, unique=True)
        last_login = Column(DateTime)
        
        def __init__(self, username):
            self.name = username
            self.last_login = datetime.datetime.now()
            # self.id = None

    # Класс - отображение таблицы активных пользователей:
    # Экземпляр этого класса = запись в таблице ActiveUsers
    class ActiveUsers(BASE):
        # Создаём таблицу активных пользователей
        __tablename__ = 'Active_users'
        id = Column(Integer, primary_key=True)
        user = Column(ForeignKey('Users.id'))
        ip_address = Column(String)
        port = Column(Integer)
        login_time = Column(DateTime)
        
        def __init__(self, user_id, ip_address, port, login_time):
            self.user = user_id
            self.ip_address = ip_address
            self.port = port
            self.login_time = login_time
            # self.id = None

    # Класс - отображение таблицы истории входов
    # Экземпляр этого класса = запись в таблице LoginHistory
    class LoginHistory(BASE):
        # Создаём таблицу истории входов
        __tablename__ = 'Login_history'
        id = Column(Integer, primary_key=True)
        name = Column(ForeignKey('Users.id'))
        date_time = Column(DateTime)
        ip = Column(String)
        port = Column(String)
        
        def __init__(self, name, date, ip, port):
            # self.id = None
            self.name = name
            self.date_time = date
            self.ip = ip
            self.port = port

    def __init__(self):
        self.ENGINE = create_engine(CONFIGS['SERVER_DATABASE'], echo=False, pool_recycle=7200)

        self.BASE.metadata.create_all(self.ENGINE)
        SESSION = sessionmaker(bind=self.ENGINE)
        self.SESS_OBJ = SESSION()

        # Если в таблице активных пользователей есть записи, то их необходимо удалить
        # Когда устанавливаем соединение, очищаем таблицу активных пользователей
        self.SESS_OBJ.query(self.ActiveUsers).delete()
        self.SESS_OBJ.commit()


    # Функция выполняющяяся при входе пользователя, записывает в базу факт входа
    def user_login(self, username, ip_address, port):
        print(username, ip_address, port)
        # Запрос в таблицу пользователей на наличие там пользователя с таким именем
        rez = self.SESS_OBJ.query(self.AllUsers).filter_by(name=username)
        print(type(rez))
        # Если имя пользователя уже присутствует в таблице, обновляем время последнего входа
        if rez.count():
            user = rez.first()
            user.last_login = datetime.datetime.now()
        # Если нет, то создаздаём нового пользователя
        else:
            # Создаем экземпляр класса self.AllUsers, через который передаем данные в таблицу
            user = self.AllUsers(username)
            self.SESS_OBJ.add(user)
            # Комит здесь нужен, чтобы присвоился ID
            self.SESS_OBJ.commit()

        # # Теперь можно создать запись в таблицу активных пользователей о факте входа.
        # # Создаем экземпляр класса self.ActiveUsers, через который передаем данные в таблицу
        new_active_user = self.ActiveUsers(user.id, ip_address, port, datetime.datetime.now())
        self.SESS_OBJ.add(new_active_user)

        # # и сохранить в историю входов
        # # Создаем экземпляр класса self.LoginHistory, через который передаем данные в таблицу
        history = self.LoginHistory(user.id, datetime.datetime.now(), ip_address, port)
        self.SESS_OBJ.add(history)

        # # Сохраняем изменения
        self.SESS_OBJ.commit()

    # Функция фиксирующая отключение пользователя
    def user_logout(self, username):
        # Запрашиваем пользователя, что покидает нас
        # получаем запись из таблицы AllUsers
        user = self.SESS_OBJ.query(self.AllUsers).filter_by(name=username).first()

        # Удаляем его из таблицы активных пользователей.
        # Удаляем запись из таблицы ActiveUsers
        self.SESS_OBJ.query(self.ActiveUsers).filter_by(user=user.id).delete()

        # Применяем изменения
        self.SESS_OBJ.commit()

    # Функция возвращает список известных пользователей со временем последнего входа.
    def users_list(self):
        query = self.SESS_OBJ.query(
            self.AllUsers.name,
            self.AllUsers.last_login,
        )
        # Возвращаем список кортежей
        return query.all()

    # Функция возвращает список активных пользователей
    def active_users_list(self):
        # Запрашиваем соединение таблиц и собираем кортежи имя, адрес, порт, время.
        query = self.SESS_OBJ.query(
            self.AllUsers.name,
            self.ActiveUsers.ip_address,
            self.ActiveUsers.port,
            self.ActiveUsers.login_time
            ).join(self.AllUsers)
        # Возвращаем список кортежей
        return query.all()

    # Функция возвращающая историю входов по пользователю или всем пользователям
    def login_history(self, username=None):
        # Запрашиваем историю входа
        query = self.SESS_OBJ.query(self.AllUsers.name,
                                   self.LoginHistory.date_time,
                                   self.LoginHistory.ip,
                                   self.LoginHistory.port
                                   ).join(self.AllUsers)
        # Если было указано имя пользователя, то фильтруем по нему
        if username:
            query = query.filter(self.AllUsers.name == username)
        return query.all()


if __name__ == '__main__':
    test_db = ServerStorage()
    # выполняем 'подключение' пользователя
    test_db.user_login('client_3', '192.168.1.4', 8887)
    test_db.user_login('client_4', '192.168.1.5', 7778)
    # выводим список кортежей - активных пользователей
    print(test_db.active_users_list())
    # выполянем 'отключение' пользователя
    # test_db.user_logout('client_1')
    # выводим список активных пользователей
    print(test_db.active_users_list())
    # запрашиваем историю входов по пользователю
    # test_db.login_history('client_1')
    # выводим список известных пользователей
    print(test_db.users_list())