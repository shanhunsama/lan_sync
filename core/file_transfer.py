"""文件传输模块"""

import os
import struct
import logging
from pathlib import Path

from .helpers import recvn, send_json, CHUNK_SIZE


def send_file_by_rel(sock, base_dir, relpath):
    """发送文件（带JSON头信息）"""
    path = Path(base_dir) / Path(relpath)
    size = path.stat().st_size
    header = {'type': 'file', 'path': relpath, 'size': size}
    send_json(sock, header)
    
    with open(path, 'rb') as f:
        while True:
            chunk = f.read(CHUNK_SIZE)
            if not chunk:
                break
            # 发送原始块长度 + 块数据
            sock.sendall(struct.pack('>I', len(chunk)))
            sock.sendall(chunk)
    
    # 用零长度块表示文件结束
    sock.sendall(struct.pack('>I', 0))
    logging.info('Sent file: %s (%d bytes)', relpath, size)


def receive_file(sock, base_dir, header):
    """接收文件（期望头信息已被接收线程读取）"""
    rel = header['path']
    size = header['size']

    # 清理传入路径以避免路径遍历或绝对路径
    rel_path = Path(rel)
    if rel_path.is_absolute() or '..' in rel_path.parts:
        logging.error('Rejected unsafe path from peer: %s', rel)
        # 仍然必须消耗传入的文件字节流以保持协议同步
        while True:
            ln_b = recvn(sock, 4)
            if not ln_b:
                raise ConnectionError('Unexpected EOF during file transfer')
            (ln,) = struct.unpack('>I', ln_b)
            if ln == 0:
                break
            chunk = recvn(sock, ln)
            if not chunk:
                raise ConnectionError('Unexpected EOF during file transfer chunk')
        return

    out_path = Path(base_dir) / rel_path
    out_path.parent.mkdir(parents=True, exist_ok=True)
    received = 0
    
    # 添加调试信息
    logging.info('Saving file to: %s', out_path)
    
    with open(str(out_path) + '.tmp', 'wb') as f:
        while True:
            ln_b = recvn(sock, 4)
            if not ln_b:
                raise ConnectionError('Unexpected EOF during file transfer')
            (ln,) = struct.unpack('>I', ln_b)
            if ln == 0:
                break
            chunk = recvn(sock, ln)
            if not chunk:
                raise ConnectionError('Unexpected EOF during file transfer chunk')
            f.write(chunk)
            received += len(chunk)
    
    # 添加文件保存确认
    logging.info('Temporary file created, size: %d bytes', received)
    
    try:
        os.replace(str(out_path) + '.tmp', out_path)
        logging.info('File successfully saved: %s (%d bytes)', rel, received)
    except Exception as e:
        logging.error('Failed to rename file %s: %s', out_path, e)
        # 如果重命名失败，尝试直接复制
        try:
            import shutil
            shutil.copy(str(out_path) + '.tmp', out_path)
            os.remove(str(out_path) + '.tmp')
            logging.info('File saved using copy method: %s', rel)
        except Exception as e2:
            logging.error('Failed to save file using copy method: %s', e2)