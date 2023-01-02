# inpe
纯python实现的内网穿透工具
# usage
1. 在内网服务器启动socks代理
```shell
python proxy-socks5.py
```
2. 在公网服务器启动服务
```shell
python proxy-web.py --web
```
3. 在内网服务器启动服务
```shell
python proxy-web.py --inte --web-addr 1.1.1.1:9999
```
4. 使用代码示例
```python
import requests
r = requests.get(
            "http://172.16.1.1:8080",
            proxies={
                "http": "socks5://1.1.1.1:8888",
                "https": "socks5://1.1.1.1:8888",
            },
            verify=False,
        )
```

# code explain
1. socketserver.py 是python的标准库，但某些时候可能服务器上没有，所以直接把代码搬了过来
2. proxy-socks5.py 是抄的代码，用于实现socks5代理
3. proxy-web.py 通过命令行启动公网服务和内网服务，建立代理隧道。