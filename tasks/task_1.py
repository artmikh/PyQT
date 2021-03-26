"""
1. Написать функцию host_ping(), в которой с помощью утилиты ping
будет проверяться доступность сетевых узлов.
Аргументом функции является список, в котором каждый сетевой узел
должен быть представлен именем хоста или ip-адресом.
В функции необходимо перебирать ip-адреса и проверять
их доступность с выводом соответствующего сообщения
(«Узел доступен», «Узел недоступен»). При этом ip-адрес
сетевого узла должен создаваться с помощью функции ip_address().
"""
from subprocess import Popen, PIPE
import ipaddress
import socket

# Добавил проверку на получение доменного имени
# Если ip адрес публичный, то ищем у него домен
# Если домена у него нет, то выдаем просто ip-адрес
def check_for_global(ip_addr, addr):
    if ip_addr.is_global:
        if socket.gethostbyaddr(str(ip_addr)):
            dn_addr = socket.gethostbyaddr(str(ip_addr))[0] # Если адрес является ip, то преобразуем его в доменное имя
            return dn_addr
        return addr
    else:
        return addr   

def host_ping(addr_list, timeout=500, times=1):
    result_list = {'Доступные адреса': "", 'Недоступные адреса': ""}

    for addr in addr_list:
        try:
            ip_addr = ipaddress.ip_address(addr)
            
        except:
            ip = socket.gethostbyname(addr) # Если адрес является доменным именем, то преобразуем его в ip
            ip_addr = ipaddress.ip_address(ip)

        ping = Popen(f'ping {ip_addr} -w {timeout} -n {times}', shell=False, stdout=PIPE)
        ping.wait()

        if ping.returncode == 0:
            result_list['Доступные адреса'] += f'{str(addr)}\n'
            ping_answer = f'{check_for_global(ip_addr, addr)} ({ip_addr}) - Адрес доступен'
            
        else:
            result_list['Недоступные адреса'] += f'{str(addr)}\n'
            ping_answer = f'{addr} ({ip_addr}) - Адрес недоступен'
        print(ping_answer)
    
    return result_list


if __name__ == '__main__':
    addr_list = ['ya.ru', '8.8.8.8', '9.99.9.9', '192.168.0.1']
    host_ping(addr_list)

