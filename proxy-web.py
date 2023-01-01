# coding:utf8
import time
from socket import *
import select
import argparse
import traceback
from concurrent.futures import ThreadPoolExecutor


class SocketTunnelServer:
    heartbeat_msg = b"Tb;\x0bM|sF*q Ew)\x0cOpSZr-C9!7XKkH\t"

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

    def exchange_loop(self, client, remote, heartbeat_socket=None):
        client_peer = client.getpeername()
        remote_peer = remote.getpeername()
        chunk_size = 8192
        try:
            # 处理数据
            while 1:
                recv_data = b""
                r, w, e = select.select([client, remote], [], [client, remote], 30)
                if e:
                    break
                if client in r:
                    recv_data = client.recv(chunk_size)
                    # print(f"client {client_peer}, {remote_peer} recv: {recv_data}")
                    send_data = recv_data.replace(self.heartbeat_msg, b"")
                    if send_data:
                        remote.send(send_data)
                if remote in r:
                    recv_data = remote.recv(chunk_size)
                    # print(f"remote {client_peer}, {remote_peer} recv: {recv_data}")
                    send_data = recv_data.replace(self.heartbeat_msg, b"")
                    if send_data:
                        client.send(send_data)
                if not r:
                    if heartbeat_socket:
                        # 检测连接是否还活着
                        heartbeat_socket.send(self.heartbeat_msg)
                    continue
                if not recv_data:
                    break
        except Exception as e:
            traceback.print_exc()
        client.shutdown()
        client.close()
        remote.shutdown()
        remote.close()
        print(f"closed {client_peer}, {remote_peer}")
        return

    def run_inte(self, web_addr="", max_thread=100, **kwargs):
        # 外网服务地址
        if web_addr:
            web_addr = web_addr.split(":")
            web_addr = (web_addr[0], int(web_addr[1]))
        else:
            web_addr = ("127.0.0.1", 9999)
        # 内网socks地址
        socks_addr = ("127.0.0.1", 9011)
        print("inte restarting")

        pool = ThreadPoolExecutor(max_workers=max_thread)
        while 1:
            web_socket = self.create_socket(connect_addr=web_addr)
            socks_socket = self.create_socket(connect_addr=socks_addr)
            pool.submit(self.exchange_loop, web_socket, socks_socket, web_socket)

    def run_web(self, max_thread=100, **kwargs):
        #
        proxy_connect_addr = ("", 9999)
        client_connect_addr = ("", 8888)
        #
        proxy_connect_socket = self.create_socket(
            bind_addr=proxy_connect_addr, listen=True
        )
        client_connect_socket = self.create_socket(
            bind_addr=client_connect_addr, listen=True
        )
        print("web starting")
        #
        pool = ThreadPoolExecutor(max_workers=max_thread)
        while 1:
            # 接收连接
            proxy_socket, proxy_addr = proxy_connect_socket.accept()
            client_socket, client_addr = client_connect_socket.accept()
            pool.submit(self.exchange_loop, client_socket, proxy_socket, proxy_socket)

    def serve_forever(self, func, **kwargs):
        while 1:
            try:
                func(**kwargs)
            except Exception as e:
                traceback.print_exc()
            time.sleep(10)


def get_cmd_args():
    parser = argparse.ArgumentParser(
        prog="Program Name (default: sys.argv[0])",
        add_help=True,
    )
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
