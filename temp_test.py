import requests
proxies = {"http": "http://127.0.0.1:30004", "https": "http://127.0.0.1:30004"}
print(requests.get("http://httpbin.org/ip", proxies=proxies, timeout=10).text)