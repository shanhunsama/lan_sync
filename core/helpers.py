"""核心工具函数模块"""

import os
import json
import struct
import hashlib
import sys
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from config_manager import ConfigManager

# 全局配置管理器实例
_config_manager = ConfigManager()

def get_performance_config():
    """获取性能配置"""
    return _config_manager.get_performance_config()

def get_chunk_size():
    """获取动态块大小"""
    config = get_performance_config()
    return config.get('chunk_size', 262144)  # 默认256KB

def get_socket_buffer_size():
    """获取套接字缓冲区大小"""
    config = get_performance_config()
    return config.get('socket_buffer_size', 1048576)  # 默认1MB

def should_disable_nagle():
    """是否禁用Nagle算法"""
    config = get_performance_config()
    return config.get('disable_nagle', True)

def get_thread_count():
    """获取并发线程数"""
    config = get_performance_config()
    return config.get('thread_count', 4)

# 保持向后兼容性
CHUNK_SIZE = get_chunk_size()

def compute_sha256(path):
    """计算文件的SHA256哈希值"""
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        while True:
            data = f.read(CHUNK_SIZE)
            if not data:
                break
            h.update(data)
    return h.hexdigest()


def build_manifest(base_dir):
    """构建文件清单"""
    manifest = {}
    base_dir = Path(base_dir)
    for root, dirs, files in os.walk(base_dir):
        for fname in files:
            fpath = Path(root) / fname
            rel = str(fpath.relative_to(base_dir)).replace('\\', '/')
            try:
                st = fpath.stat()
            except OSError:
                continue
            size = st.st_size
            mtime = int(st.st_mtime)
            sha = compute_sha256(fpath)
            manifest[rel] = {'size': size, 'mtime': mtime, 'sha256': sha}
    return manifest


def send_json(sock, obj):
    """发送JSON数据"""
    data = json.dumps(obj, ensure_ascii=False).encode('utf-8')
    sock.sendall(struct.pack('>I', len(data)))
    sock.sendall(data)


def recv_json(sock):
    """接收JSON数据"""
    header = recvn(sock, 4)
    if not header:
        return None
    (length,) = struct.unpack('>I', header)
    data = recvn(sock, length)
    if not data:
        return None
    return json.loads(data.decode('utf-8'))


def recvn(sock, n):
    """接收指定数量的字节"""
    buf = b''
    while len(buf) < n:
        chunk = sock.recv(n - len(buf))
        if not chunk:
            return None
        buf += chunk
    return buf