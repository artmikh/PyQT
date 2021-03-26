"""
2. Написать функцию host_range_ping() для перебора ip-адресов из заданного диапазона.
Меняться должен только последний октет каждого адреса.
По результатам проверки должно выводиться соответствующее сообщение.
"""
from ipaddress import ip_address
from task_1 import host_ping

def host_range_ping():
    ip_list = []
    start_ip = input('Введите стартовый ip адрес: ')
    q = int(input('Сколько адресов проверять: '))

    i = 0
    while i < q:
        ip_list.append(str(ip_address(start_ip) + i))
        i += 1
    
    return host_ping(ip_list)
    # print(host_ping(ip_list))


if __name__ == '__main__':
    host_range_ping()
