import subprocess

process = []

while True:
    action = input(
        'Выберите действие: '
        'q - ВЫХОД, '
        's - ЗАПУСТИТЬ СЕРВЕР, '
        'с - ЗАПУСТИТЬ КЛИЕНТОВ, '
        'x - ЗАКРЫТЬ ВСЕ ОКНА: '
        )

    if action == 'q':
        break
    elif action == 's':
        process.append(subprocess.Popen(
                                    'python server.py',
                                    creationflags=subprocess.CREATE_NEW_CONSOLE)
                                    )
    elif action == 'c':
        quantity = input('Сколько клиентов запустить?: ')
        try:
            qInt = int(quantity)
        except:
            print('Вводить можно только цифру')
        for i in range(1, qInt+1):
            process.append(subprocess.Popen(
                                    f'python client.py -n test{i}', 
                                    creationflags=subprocess.CREATE_NEW_CONSOLE)
                                    )
    elif action == 'x':
        while process:
            victim = process.pop()
            victim.kill()
