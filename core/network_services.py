"""网络服务模块 - 提供单向传输的网络服务"""

import socket
import logging
import threading
from pathlib import Path

# 添加项目根目录到Python路径
import sys
project_root = Path(__file__).parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from .helpers import get_socket_buffer_size, should_disable_nagle, get_thread_count
from .file_transfer import send_file_by_rel, receive_file
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


def create_socket_with_performance_settings():
    """创建套接字并应用性能配置"""
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    
    # 应用性能配置
    buffer_size = get_socket_buffer_size()
    disable_nagle = should_disable_nagle()
    
    # 设置套接字缓冲区大小
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_SNDBUF, buffer_size)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, buffer_size)
    
    # 禁用Nagle算法（如果配置要求）
    if disable_nagle:
        sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
    
    return sock

def run_send(host, port, folder, log_callback):
    """发送文件到接收方（使用性能配置）"""
    try:
        sock = create_socket_with_performance_settings()
        sock.connect((host, port))
        log_callback(f'已连接到 {host}:{port}')
        
        # 发送文件夹信息
        send_folder_info(sock, folder, log_callback)
        
        sock.close()
        log_callback('发送完成')
    except Exception as e:
        log_callback(f'发送错误: {e}')

def run_receive(port, folder, log_callback, bind_host='0.0.0.0'):
    """接收文件（使用性能配置）"""
    try:
        sock = create_socket_with_performance_settings()
        sock.bind((bind_host, port))
        sock.listen(1)
        log_callback(f'监听端口 {port}，等待连接...')
        
        conn, addr = sock.accept()
        log_callback(f'接收到来自 {addr[0]}:{addr[1]} 的连接')
        
        # 接收文件夹信息
        receive_folder_info(conn, folder, log_callback)
        
        conn.close()
        sock.close()
        log_callback('接收完成')
    except Exception as e:
        log_callback(f'接收错误: {e}')