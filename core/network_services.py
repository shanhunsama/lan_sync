"""网络服务模块 - 提供单向传输的网络服务"""

import socket
import logging

from .unidirectional import handle_unidirectional_send, handle_unidirectional_receive


def run_send(host, port, base_dir, log_callback=None):
    """运行发送方模式：主动连接接收方并发送文件"""
    log_func = log_callback or logging.info
    log_func('Connecting to receiver %s:%d ...', host, port)
    with socket.create_connection((host, port), timeout=30) as sock:
        log_func('Connected to receiver %s:%d', host, port)
        handle_unidirectional_send(sock, base_dir, log_callback)


def run_receive(port, base_dir, log_callback=None, bind='0.0.0.0'):
    """运行接收方模式：启动监听服务等待发送方连接"""
    log_func = log_callback or logging.info
    log_func('Listening for sender on %s:%d', bind, port)
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        s.bind((bind, port))
        s.listen(1)
        conn, addr = s.accept()
        log_func('Accepted connection from sender %s:%d', addr[0], addr[1])
        with conn:
            handle_unidirectional_receive(conn, base_dir, log_callback)