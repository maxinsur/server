import os
import requests
import sqlite3
import time
import json

# Создание соединения с базой данных (будет создана новая, если не существует)
base_dir = os.path.dirname(os.path.abspath(__file__))
db_path = os.path.join(base_dir, 'mydatabase.db')

# Создание соединения с базой данных
conn = sqlite3.connect(db_path)

# Создание курсора
c = conn.cursor()

# Создание таблицы
c.execute('''
    CREATE TABLE IF NOT EXISTS mining_data
    (timestamp TEXT, rig_id TEXT, total_hr REAL, coin TEXT,
    power_usage REAL, remote_ip TEXT, energy_cost REAL, coin_id TEXT,
    daily_revenue_usd REAL, daily_cost_usd REAL, estimated_rewards REAL,
    Total_USDT_Rewards REAL, Last_Price REAL, If_sale_now REAL)
''')

# Создание словаря для хранения накопительной суммы daily_revenue_usd для каждого rig_id
total_usdt_rewards = {}

# Создание словаря для хранения накопительной суммы estimated_rewards для каждой монеты
total_estimated_rewards = {}

# Функция для добавления данных в таблицу
def add_data_to_db(data, coin):
    with conn:
        # Вставка данных в таблицу
        c.execute("INSERT INTO mining_data(timestamp, rig_id, coin, total_hr, coin, power_usage, remote_ip, energy_cost, coin_id, daily_revenue_usd, daily_cost_usd, estimated_rewards) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)", data)

        # Вычисление текущей суммы дохода для данной монеты
        total_usdt_rewards[coin] = total_usdt_rewards.get(coin, 0) + data[9]

        # Вычисление текущей суммы estimated_rewards для данной монеты
        total_estimated_rewards[coin] = total_estimated_rewards.get(coin, 0) + data[11]

        # Вычисление последней цены
        last_price = data[9] / data[11] if data[11] else 0

        # Вычисление If_sale_now
        if_sale_now = last_price * total_estimated_rewards[coin]

        # Обновление только что вставленной строки новыми значениями Total_USDT_Rewards, Last_Price и If_sale_now
        c.execute("UPDATE mining_data SET Total_USDT_Rewards = ?, Last_Price = ?, If_sale_now = ? WHERE rowid = last_insert_rowid()", (total_usdt_rewards[coin], last_price, if_sale_now))




# Функция для получения данных о монете
def get_coin(coin, coin_data):
    for coin_info in coin_data:
        try:
            coin_coin, coin_name, hashrate_unit = coin_info
            if coin_coin == coin:
                return coin_name, hashrate_unit
        except ValueError:
            print(f"Warning: could not unpack line: {coin_info}")
    return "Unknown", ""

# Функция для получения ID монеты
def get_coin_id(tag):
    url = "https://whattomine.com/coins.json"
    response = requests.get(url)
    coins_data = response.json()
    for coin in coins_data["coins"]:
        if coins_data["coins"][coin]["tag"] == tag:  # Изменение здесь
            return coins_data["coins"][coin]["id"]
    return ""

# Функция для получения курса обмена
def get_exchange_rate():
    url = "https://www.cbr-xml-daily.ru/daily_json.js"
    response = requests.get(url)
    return response.json()['Valute']['USD']['Value']

# Функция для получения оценки вознаграждения
def get_estimated_rewards(coin_id, hashrate):
    url = f"https://whattomine.com/coins/{coin_id}.json?hr={hashrate}"
    response = requests.get(url)
    if response.status_code == 200:
        data = response.json()
        estimated_rewards = data.get('estimated_rewards')
        if estimated_rewards is not None:
            return estimated_rewards
        else:
            print("Key 'estimated_rewards' not found in the data")
    else:
        print("Error making request")
    return None

# Функция для получения оценки дохода
def get_estimated_revenue(coin_id, hashrate):
    url = f"https://whattomine.com/coins/{coin_id}.json?hr={hashrate}"
    response = requests.get(url)
    if response.status_code == 200:
        data = response.json()
        estimated_revenue = data.get('revenue')
        if estimated_revenue is not None:
            return estimated_revenue
        else:
            print("Key 'revenue' not found in the data")
    else:
        print("Error making request")
    return None

def get_server_data(api_url, headers, params):
    response = requests.get(api_url, headers=headers, params=params, timeout=10)  # Ожидаем ответ в течение 10 секунд
    data = response.json()
    coin = data.get('profiles')[0].get('coin') if data.get('profiles') else "No coin found"
    miner_stats = data.get('minerStats')
    total_hr = float(miner_stats[0].get('total_hr')) if miner_stats and miner_stats[0].get('total_hr') else 0.0
    while total_hr >= 1000:
        total_hr /= 1000
    power_usage = 0
    if 'gpu_power' in data:
        gpu_power = data.get('gpu_power')
        power_usage = (sum(gpu_power) + 100) / 1000
    remote_ip = data.get('remote_ip') if data.get('remote_ip') else "No IP found"
    return coin, total_hr, power_usage, remote_ip



# Считывание данных из файла config.txt
with open('C:/Users/Maxim/Desktop/MyPyProgram/math/config.txt', 'r') as f:
    lines = [line.strip().split('=')[1] for line in f.readlines() if '=' in line]
    rig_ids = lines[0].split(',')
    energy_costs_info = lines[1].split(';')
    energy_costs = {}
    for info in energy_costs_info:
        rig_ids_for_cost, cost = info.split('-')
        for rig_id in rig_ids_for_cost.split(','):
            energy_costs[rig_id.strip()] = float(cost)  # используем rig_id как строку
    api_url = lines[2]
    login = lines[3]
    password = lines[4]
    params = {"request": "stats"}

# Функция для получения токена
def get_auth_token(login, password):
    url = "https://os.dog/api/v2/auth/login"
    data = {"login": login, "password": password}
    headers = {'Content-Type': 'application/json'}

    try:
        response = requests.post(url, data=json.dumps(data), headers=headers)
        response_data = response.json()
        if response.status_code == 200 and 'authToken' in response_data:
            return response_data['authToken']
        else:
            print("Error getting auth token:", response.status_code, response_data)
    except requests.exceptions.RequestException as e:
        print("There was an error getting auth token: ", e)

    return ""

# Получение начального токена
auth_token = get_auth_token(login, password)
headers = {"authToken": auth_token}

# Функция для получения затрат на энергию
def get_energy_cost(rig_id, energy_costs):
    return energy_costs.get(str(rig_id), 0.0)  # передаем rig_id как строку

# Функция для обновления нового столбца
def update_total_rewards():
    with conn:
        c.execute('UPDATE mining_data SET Total_USDT_Rewards = (SELECT SUM(daily_revenue_usd) FROM mining_data)')

def update_data():
    for rig_id in rig_ids:
        try:
            api_url_with_rig_id = api_url + rig_id
            coin, total_hr, power_usage, remote_ip = get_server_data(api_url_with_rig_id, headers, params)  # Правильное присвоение значений

            # Получение затрат на энергию для этого rig
            energy_cost = get_energy_cost(rig_id, energy_costs)  # Используйте rig_id вместо remote_ip

            coin_id = get_coin_id(coin)

            # Получение ежедневной выручки
            daily_revenue_usd = 0.0
            if coin_id:
                estimated_revenue = get_estimated_revenue(coin_id, total_hr)
                if estimated_revenue is not None:
                    estimated_revenue = estimated_revenue.replace(",", "").replace("$", "")
                    estimated_revenue = float(estimated_revenue)  # Убедимся, что estimated_revenue преобразуется в число
                    daily_revenue_usd = estimated_revenue / 1440

            estimated_rewards = 0.0
            if coin_id:
                estimated_rewards = get_estimated_rewards(coin_id, total_hr)
                if estimated_rewards is not None:
                    estimated_rewards = estimated_rewards.replace(",", "")
                    estimated_rewards = float(estimated_rewards)  # Убедимся, что estimated_rewards преобразуется в число
                    estimated_rewards = estimated_rewards / 1440

            exchange_rate = get_exchange_rate()
            daily_cost_usd = (energy_cost * power_usage / exchange_rate) / 60

            # Создание кортежа с данными
            timestamp = time.strftime("%Y-%m-%d %H:%M:%S", time.gmtime())
            data = (timestamp, rig_id, coin, total_hr, coin, power_usage, remote_ip,
                    energy_cost, coin_id, daily_revenue_usd, daily_cost_usd, estimated_rewards)
            add_data_to_db(data, coin)


        except requests.exceptions.ConnectionError as e:
                ("ConnectionError occurred:", e)


# Бесконечный цикл, который обновляет данные каждые 5 минут
auth_token_update_time = time.time()  # начальное время обновления токена
while True:
    try:
        # Если с последнего обновления токена прошло более 10 часов, обновляем токен
        if time.time() - auth_token_update_time >= 10*60*60:
            auth_token = get_auth_token(login, password)
            headers = {"authToken": auth_token}
            auth_token_update_time = time.time()

        update_data()
        time.sleep(60)
    except requests.exceptions.RequestException as e:
        ("There was an error: ", e)
        time.sleep(60)
