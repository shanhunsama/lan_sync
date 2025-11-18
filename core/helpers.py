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

# 新增性能优化函数
def should_use_memory_mapping():
    """是否使用内存映射"""
    config = get_performance_config()
    return config.get('use_memory_mapping', True)

def should_use_stream_protocol():
    """是否使用流式协议"""
    config = get_performance_config()
    return config.get('use_stream_protocol', True)

def should_use_dynamic_chunk_size():
    """是否使用动态块大小"""
    config = get_performance_config()
    return config.get('dynamic_chunk_size', True)

def get_max_chunk_size():
    """获取最大块大小"""
    config = get_performance_config()
    return config.get('max_chunk_size', 1048576)  # 1MB

def get_min_chunk_size():
    """获取最小块大小"""
    config = get_performance_config()
    return config.get('min_chunk_size', 65536)  # 64KB

def get_compression_threshold():
    """获取压缩阈值"""
    config = get_performance_config()
    return config.get('compression_threshold', 1048576)  # 1MB

def should_enable_compression():
    """是否启用压缩"""
    config = get_performance_config()
    return config.get('enable_compression', False)

def should_use_adaptive_threading():
    """是否使用自适应线程数"""
    config = get_performance_config()
    return config.get('adaptive_threading', True)

def calculate_optimal_chunk_size(file_size):
    """计算最优块大小"""
    if not should_use_dynamic_chunk_size():
        return get_chunk_size()
    
    min_size = get_min_chunk_size()
    max_size = get_max_chunk_size()
    
    # 根据文件大小动态调整块大小
    if file_size < 10 * 1024 * 1024:  # 小于10MB
        return min_size
    elif file_size < 100 * 1024 * 1024:  # 10MB-100MB
        return min(max_size // 4, max_size)
    else:  # 大于100MB
        return max_size

def calculate_optimal_threads(file_size):
    """计算最优线程数"""
    if not should_use_adaptive_threading():
        return get_thread_count()
    
    base_threads = get_thread_count()
    
    # 根据文件大小动态调整线程数
    if file_size < 5 * 1024 * 1024:  # 小于5MB
        return min(2, base_threads)
    elif file_size < 50 * 1024 * 1024:  # 5MB-50MB
        return base_threads
    else:  # 大于50MB
        return min(base_threads * 2, 16)  # 最多16线程

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