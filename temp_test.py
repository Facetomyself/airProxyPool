import requests


def fetch_proxy_ip() -> str:
    proxies = {"http": "http://127.0.0.1:30004", "https": "http://127.0.0.1:30004"}
    response = requests.get("http://httpbin.org/ip", proxies=proxies, timeout=10)
    return response.text


if __name__ == "__main__":
    print(fetch_proxy_ip())
