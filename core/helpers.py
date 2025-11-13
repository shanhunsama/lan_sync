"""核心工具函数模块"""

import os
import json
import struct
import hashlib
from pathlib import Path

# 全局配置
CHUNK_SIZE = 64 * 1024


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