# coding:utf8
import time
from socket import *
import select
import argparse
import traceback
from concurrent.futures import ThreadPoolExecutor


class SocketTunnelServer:
    def create_socket(self, connect_addr=None, bind_addr=None, listen=False):
        socket_obj = socket(AF_INET, SOCK_STREAM)
        socket_obj.setsockopt(SOL_SOCKET, SO_REUSEADDR, 1)
        if connect_addr:
            socket_obj.connect(connect_addr)
        if bind_addr:
            socket_obj.bind(bind_addr)
        if listen:
            socket_obj.listen(128)
        return socket_obj

    def tunnel_worker(self, client, remote):
        try:
            # 处理数据
            while 1:
                data = None
                r, w, e = select.select([client, remote], [], [])
                if client in r:
                    data = client.recv(4096)
                    if data:
                        remote.send(data)
                if remote in r:
                    data = remote.recv(4096)
                    if data:
                        client.send(data)
                if not data:
                    break
        except Exception as e:
            traceback.print_exc()
        client.close()
        remote.close()
        return

    def run_inte(self, web_addr="", max_thread=100, **kwargs):
        # 外网服务地址
        if web_addr:
            web_addr = web_addr.split(":")
            web_addr[1] = int(web_addr[1])
            web_addr = tuple(web_addr)
        else:
            web_addr = ("127.0.0.1", 9999)
        # 内网socks地址
        socks_addr = ("127.0.0.1", 9011)
        print("inte restarting")

        pool = ThreadPoolExecutor(max_workers=max_thread)
        while 1:
            server_socket = self.create_socket(connect_addr=web_addr)
            socks_socket = self.create_socket(connect_addr=socks_addr)
            pool.submit(self.tunnel_worker, server_socket, socks_socket)

        return

    def run_web(self, max_thread=100, **kwargs):
        #
        proxy_connect_addr = ("", 9999)
        client_connect_addr = ("", 8888)
        #
        server_for_proxy_socket = self.create_socket(
            bind_addr=proxy_connect_addr, listen=True
        )
        server_for_client_socket = self.create_socket(
            bind_addr=client_connect_addr, listen=True
        )
        print("web starting")
        #
        pool = ThreadPoolExecutor(max_workers=max_thread)
        #
        while 1:
            # 接收连接
            proxy_socket, proxy_addr = server_for_proxy_socket.accept()
            client_socket, client_addr = server_for_client_socket.accept()
            pool.submit(self.tunnel_worker, client_socket, proxy_socket)
        return

    def serve_forever(self, func, **kwargs):
        while 1:
            try:
                func(**kwargs)
            except Exception as e:
                traceback.print_exc()
            time.sleep(10)
        return


def get_cmd_args():
    parser = argparse.ArgumentParser(
        prog="Program Name (default: sys.argv[0])",
        add_help=True,
    )
    # 私募基金
    parser.add_argument("--web", action="store_true", help="")
    parser.add_argument("--inte", action="store_true", help="")
    parser.add_argument("--web-addr", action="store", default="", help="")
    parser.add_argument("--max-thread", action="store", default="100", help="")
    return parser.parse_args()


def main():
    args = get_cmd_args()
    sts = SocketTunnelServer()
    #
    max_thread = int(args.max_thread)
    #
    if args.web:
        sts.serve_forever(sts.run_web, max_thread=max_thread)
    elif args.inte:
        sts.serve_forever(sts.run_inte, web_addr=args.web_addr, max_thread=max_thread)
    return


if __name__ == "__main__":
    main()
