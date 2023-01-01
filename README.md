# rpt
reverse proxy tunnel, 纯python实现的反向代理隧道
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