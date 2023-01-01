from socket import *

import requests


def client():

    for i in range(2):

        r = requests.get(
            "https://httpbin.org/anything",
            # "https://www.baidu.com",
            proxies={
                "http": "socks5://127.0.0.1:8888",
                "https": "socks5://127.0.0.1:8888",
            },
            verify=False,
        )
        print(r.text)

    return


if __name__ == "__main__":
    client()
