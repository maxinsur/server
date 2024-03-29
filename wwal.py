import subprocess
import json
import tempfile
from concurrent.futures import ThreadPoolExecutor

def create_wallet():
    search_values = ["max", "wart"]

    with tempfile.NamedTemporaryFile(suffix='.json', delete=False) as temp_file:
        wallet_name = temp_file.name[:-5]  # Убираем расширение .json из имени временного файла

        try:
            result = subprocess.run(['./wart-wallet-linux', '--create', '-f', wallet_name], capture_output=True, text=True)
            print(f"STDOUT for {wallet_name}:", result.stdout)
            print(f"STDERR for {wallet_name}:", result.stderr)

            if result.returncode == 0:
                try:
                    json_start = result.stdout.find('{')
                    if json_start != -1:
                        output = result.stdout[json_start:]
                        wallet_info = json.loads(output)
                    else:
                        raise ValueError("JSON объект не найден в ответе")

                    address = wallet_info.get("address", "")
                    if any(address.startswith(value) or address.endswith(value) for value in search_values):
                        print(f"Найден удовлетворяющий адрес в {wallet_name}:")
                        print(f"Address: {wallet_info['address']}")
                        print(f"PrivateKey: {wallet_info['privateKey']}")
                        print(f"PublicKey: {wallet_info['publicKey']}")
                        return wallet_info  # Возвращаем информацию о кошельке
                    else:
                        print(f"Адрес {wallet_name} не удовлетворяет требованиям.")
                except (ValueError, json.JSONDecodeError) as e:
                    print(f"Ошибка при разборе ответа для {wallet_name}: {e}")
            else:
                print(f"Произошла ошибка при создании кошелька {wallet_name}.")
        finally:
            # Удаляем временный файл в блоке finally, чтобы гарантировать его удаление
            print(f"Удаляем временный файл {wallet_name}.")
            temp_file.close()
            subprocess.run(['rm', '-f', wallet_name])  # Удаляем файл

def main():
    with ThreadPoolExecutor(max_workers=72) as executor:  # Устанавливаем количество одновременных потоков
        wallets = []
        while not wallets:
            futures = [executor.submit(create_wallet) for _ in range(72)]
            for future in futures:
                wallet = future.result()
                if wallet:
                    wallets.append(wallet)
                    # Если найден кошелек, выводим информацию о нем
                    print(f"Найден кошелек:")
                    print(f"Address: {wallet['address']}")
                    print(f"PrivateKey: {wallet['privateKey']}")
                    print(f"PublicKey: {wallet['publicKey']}")
                    break  # Прерываем цикл, так как уже найден нужный кошелек

if name == "main":
    main()
