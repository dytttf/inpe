# coding:utf8
import os
import re
import sys
import time
from socket import *
import select
import argparse
from concurrent.futures import ThreadPoolExecutor
import logging


def get_logger(filename):
    """"""
    # 取文件名 不带后缀
    filename = filename.split(os.sep)[-1].split(".")[0]
    _logger = logging.getLogger(filename)
    # 标准输出流
    std = logging.StreamHandler(sys.stdout)
    _logger.addHandler(std)

    # 定制标准输出日志格式
    formatter = logging.Formatter(
        "[%(asctime)s] [%(levelname)s] [%(filename)s] [%(lineno)d] - %(message)s"
    )
    std.setFormatter(formatter)
    _logger.setLevel(logging.DEBUG)
    return _logger


logger = get_logger(__file__)


class SocketTunnelServer:
    heartbeat_msg = b"Tb;\x0bM|sF*q Ew)\x0cOpSZr-C9!7XKkH\t"

    def create_socket(
        self, connect_addr=None, bind_addr=None, listen=False, reuse=True
    ):
        socket_obj = socket(AF_INET, SOCK_STREAM)
        socket_obj.settimeout(300)
        if reuse:
            socket_obj.setsockopt(SOL_SOCKET, SO_REUSEADDR, 1)
        if connect_addr:
            socket_obj.connect(connect_addr)
        if bind_addr:
            socket_obj.bind(bind_addr)
        if listen:
            socket_obj.listen(128)
        return socket_obj

    def exchange_loop(self, client, remote, heartbeat_socket=None):
        chunk_size = 8192
        client_tag = ""
        remote_tag = ""
        try:
            client_tag = re.search("(laddr.*?)>", str(client)).group(1)
            remote_tag = re.search("(laddr.*?)>", str(remote)).group(1)
            if "laddr" not in client_tag or "raddr" not in client_tag:
                raise Exception(f"client connect failed: {client_tag}, {remote_tag}")
            if "laddr" not in remote_tag or "raddr" not in remote_tag:
                raise Exception(f"remote connect failed: {client_tag}, {remote_tag}")

            # 处理数据
            while 1:
                recv_data = b""
                r, w, e = select.select([client, remote], [], [client, remote], 30)
                if e:
                    break
                if client in r:
                    recv_data = client.recv(chunk_size)
                    # logger.debug(f"client {client_tag}, {remote_tag} recv: {recv_data}")
                    send_data = recv_data.replace(self.heartbeat_msg, b"")
                    # 心跳数据是需要抛弃的 不需要响应
                    if send_data:
                        remote.send(send_data)
                if remote in r:
                    recv_data = remote.recv(chunk_size)
                    # logger.debug(f"remote {client_tag}, {remote_tag} recv: {recv_data}")
                    send_data = recv_data.replace(self.heartbeat_msg, b"")
                    # 心跳数据是需要抛弃的 不需要响应
                    if send_data:
                        client.send(send_data)
                if not r:
                    if heartbeat_socket:
                        # 心跳 检测连接是否还活着
                        logger.debug(f"heartbeat {client_tag}, {remote_tag}: start")
                        heartbeat_socket.send(self.heartbeat_msg)
                    continue
                if not recv_data:
                    # logger.debug(f"no recv_data {client_tag}, {remote_tag}")
                    break
        except Exception as e:
            logger.exception(e)
        try:
            client.close()
        except Exception as e:
            logger.exception(e)
        try:
            remote.close()
        except Exception as e:
            logger.exception(e)
        # logger.debug(f"closed {client_tag}, {remote_tag}")
        return

    def inte_worker(self, web_addr, socks_addr):
        while 1:
            try:
                web_socket = self.create_socket(connect_addr=web_addr, reuse=False)
                socks_socket = self.create_socket(connect_addr=socks_addr, reuse=False)
                # logger.debug("{}, {}".format(web_socket, socks_socket))
                self.exchange_loop(web_socket, socks_socket, web_socket)
            except Exception as e:
                logger.exception(e)
                time.sleep(10)

    def run_inte(self, web_addr="", max_thread=100, **kwargs):
        """
            内网服务
                主动发起链接
        Args:
            web_addr:
            max_thread:
            **kwargs:

        Returns:

        """
        # 外网服务地址
        if web_addr:
            web_addr = web_addr.split(":")
            web_addr = (web_addr[0], int(web_addr[1]))
        else:
            web_addr = ("127.0.0.1", 9999)
        # 内网socks地址
        socks_addr = ("127.0.0.1", 9011)
        logger.debug("inte restarting")

        pool = ThreadPoolExecutor(max_workers=max_thread)
        for i in range(max_thread):
            time.sleep(0.3)
            pool.submit(self.inte_worker, web_addr, socks_addr)
        pool.shutdown()

    def run_web(self, max_thread=100, **kwargs):
        """
            公网服务
                被动接收链接
        Args:
            max_thread:
            **kwargs:

        Returns:

        """
        start = time.time()
        max_life = kwargs.get("max_life", 0)
        #
        proxy_connect_addr = ("", 9999)
        client_connect_addr = ("", 8887)
        #
        proxy_connect_socket = self.create_socket(
            bind_addr=proxy_connect_addr, listen=True
        )
        client_connect_socket = self.create_socket(
            bind_addr=client_connect_addr, listen=True
        )
        logger.debug("web starting")
        #
        proxy_connect_count = 0
        client_connect_count = 0
        pool = ThreadPoolExecutor(max_workers=max_thread)
        try:
            while 1:
                if 0 < max_life < time.time() - start:
                    logger.info("最大持续时间到达，主动停止")
                    break
                # 接收连接
                proxy_socket, proxy_addr = proxy_connect_socket.accept()
                proxy_connect_count += 1
                if "raddr" not in str(proxy_socket):
                    try:
                        proxy_socket.close()
                    except Exception as e:
                        logger.exception(e)
                    continue
                client_socket, client_addr = client_connect_socket.accept()
                client_connect_count += 1
                pool.submit(
                    self.exchange_loop, client_socket, proxy_socket, proxy_socket
                )
                print(
                    f"proxy_connect_count:{proxy_connect_count}, client_connect_count:{client_connect_count}",
                    end="",
                )
                time.sleep(0.5)
        except Exception as e:
            raise e
        finally:
            pool.shutdown(wait=False, cancel_futures=True)

    def serve_forever(self, func, **kwargs):
        start = time.time()
        max_life = kwargs.get("max_life", 0)
        while 1:
            if 0 < max_life < time.time() - start:
                logger.info("最大持续时间到达，主动停止")
                break
            try:
                func(**kwargs)
            except Exception as e:
                logger.exception(e)
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
    parser.add_argument(
        "--max-life", action="store", default="3600", help="最大存活时间 单位 s 避免浪费流量"
    )
    return parser.parse_args()


def main():
    args = get_cmd_args()
    sts = SocketTunnelServer()
    #
    max_thread = int(args.max_thread)
    max_life = int(args.max_life)
    #
    if args.web:
        sts.serve_forever(sts.run_web, max_thread=max_thread, max_life=max_life)
    elif args.inte:
        sts.serve_forever(sts.run_inte, web_addr=args.web_addr, max_thread=max_thread)
    return


if __name__ == "__main__":
    main()
