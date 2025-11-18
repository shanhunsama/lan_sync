"""文件传输模块"""

import os
import struct
import logging
from pathlib import Path

from .helpers import recvn, send_json, get_chunk_size, get_socket_buffer_size, should_disable_nagle
from .file_transfer_optimized import send_file_by_rel_optimized, receive_file_optimized

def send_file_by_rel(sock, base_dir, relpath):
    """发送文件（带JSON头信息）- 支持优化模式"""
    # 检查是否启用优化
    from .helpers import should_use_stream_protocol, should_use_memory_mapping
    
    if should_use_stream_protocol() or should_use_memory_mapping():
        # 使用优化版本
        return send_file_by_rel_optimized(sock, base_dir, relpath)
    else:
        # 使用传统版本
        return _send_file_by_rel_legacy(sock, base_dir, relpath)

def _send_file_by_rel_legacy(sock, base_dir, relpath):
    """传统文件发送实现"""
    path = Path(base_dir) / Path(relpath)
    size = path.stat().st_size
    header = {'type': 'file', 'path': relpath, 'size': size}
    send_json(sock, header)
    
    chunk_size = get_chunk_size()
    
    with open(path, 'rb') as f:
        while True:
            chunk = f.read(chunk_size)
            if not chunk:
                break
            sock.sendall(struct.pack('>I', len(chunk)))
            sock.sendall(chunk)
    
    sock.sendall(struct.pack('>I', 0))
    logging.info('Sent file: %s (%d bytes)', relpath, size)

def receive_file(sock, base_dir, header):
    """接收文件（期望头信息已被接收线程读取）- 支持优化模式"""
    # 检查是否启用优化
    from .helpers import should_use_stream_protocol
    
    if should_use_stream_protocol():
        # 使用优化版本
        return receive_file_optimized(sock, base_dir, header)
    else:
        # 使用传统版本
        return _receive_file_legacy(sock, base_dir, header)

def _receive_file_legacy(sock, base_dir, header):
    """传统文件接收实现"""
    rel = header['path']
    size = header['size']

    rel_path = Path(rel)
    if rel_path.is_absolute() or '..' in rel_path.parts:
        logging.error('Rejected unsafe path from peer: %s', rel)
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
    
    logging.info('Temporary file created, size: %d bytes', received)
    
    try:
        os.replace(str(out_path) + '.tmp', out_path)
        logging.info('File successfully saved: %s (%d bytes)', rel, received)
    except Exception as e:
        logging.error('Failed to rename file %s: %s', out_path, e)
        try:
            import shutil
            shutil.copy(str(out_path) + '.tmp', out_path)
            os.remove(str(out_path) + '.tmp')
            logging.info('File saved using copy method: %s', rel)
        except Exception as e2:
            logging.error('Failed to save file using copy method: %s', e2)