"""
简单的局域网文件同步工具（支持双向和单向模式）

运行方式（示例）:
  双向同步模式:
    监听方（机器 A）: python sync.py --listen --port 9000
    连接方（机器 B）: python sync.py --connect 192.168.1.100 --port 9000

  单向传输模式（发送方 -> 接收方）:
    发送方: python sync.py --send --port 9000
    接收方: python sync.py --receive 192.168.1.100 --port 9000

在当前工作目录下运行脚本（脚本会同步该目录及子目录）。

协议概述：
- 双方交换清单（relative path, size, mtime, sha256）
- 双向模式：双方各生成想要从对方获取的文件列表并发送请求
- 单向模式：发送方发送所有文件给接收方
- 传输使用简单 JSON 报文（4 字节长度前缀 + JSON）和原始字节流传输文件内容

注意：该脚本以简洁为主，适合受信任的局域网环境；未实现认证和加密。
"""

import os
import sys
import time
import json
import socket
import struct
import hashlib
import argparse
import threading
import logging
from pathlib import Path

# 将日志配置移到模块级别，避免重复配置
if not logging.getLogger().handlers:
    logging.basicConfig(level=logging.INFO, format='[%(asctime)s] %(message)s')

CHUNK_SIZE = 64 * 1024

# --- helpers ---

def compute_sha256(path):
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        while True:
            data = f.read(CHUNK_SIZE)
            if not data:
                break
            h.update(data)
    return h.hexdigest()


def build_manifest(base_dir):
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
            manifest[rel] = { 'size': size, 'mtime': mtime, 'sha256': sha }
    return manifest


def send_json(sock, obj):
    data = json.dumps(obj, ensure_ascii=False).encode('utf-8')
    sock.sendall(struct.pack('>I', len(data)))
    sock.sendall(data)


def recv_json(sock):
    header = recvn(sock, 4)
    if not header:
        return None
    (length,) = struct.unpack('>I', header)
    data = recvn(sock, length)
    if not data:
        return None
    return json.loads(data.decode('utf-8'))


def recvn(sock, n):
    buf = b''
    while len(buf) < n:
        chunk = sock.recv(n - len(buf))
        if not chunk:
            return None
        buf += chunk
    return buf

# send a file preceded by a JSON header that describes the file
def send_file_by_rel(sock, base_dir, relpath):
    path = Path(base_dir) / Path(relpath)
    size = path.stat().st_size
    header = { 'type': 'file', 'path': relpath, 'size': size }
    send_json(sock, header)
    with open(path, 'rb') as f:
        while True:
            chunk = f.read(CHUNK_SIZE)
            if not chunk:
                break
            # send raw chunk length + chunk
            sock.sendall(struct.pack('>I', len(chunk)))
            sock.sendall(chunk)
    # signal end of file with zero-length chunk
    sock.sendall(struct.pack('>I', 0))
    logging.info('Sent file: %s (%d bytes)', relpath, size)

# receive file (expects header has been read already by receiver thread when receiving a 'file' type message)
def receive_file(sock, base_dir, header):
    rel = header['path']
    size = header['size']

    # sanitize incoming path to avoid path traversal or absolute paths
    rel_path = Path(rel)
    if rel_path.is_absolute() or '..' in rel_path.parts:
        logging.error('Rejected unsafe path from peer: %s', rel)
        # must still consume the incoming file byte-stream to keep protocol in sync
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
    os.replace(str(out_path) + '.tmp', out_path)
    logging.info('Received file: %s (%d bytes)', rel, received)


# --- 单向传输逻辑 ---

def handle_unidirectional_send(sock, base_dir, log_callback=None):
    """发送方逻辑：发送所有文件给接收方"""
    base_dir = Path(base_dir)
    my_manifest = build_manifest(base_dir)
    log_func = log_callback or logging.info
    log_func('Built local manifest with %d files', len(my_manifest))
    
    # 发送模式标识
    send_json(sock, {'type': 'mode', 'mode': 'send'})
    
    # 发送文件清单
    send_json(sock, {'type': 'manifest', 'manifest': my_manifest})
    log_func('Sent manifest with %d files', len(my_manifest))
    
    # 等待接收方确认
    msg = recv_json(sock)
    if not msg or msg.get('type') != 'ready':
        log_func('Expected ready message from receiver, got: %s', msg)
        return
    
    # 发送所有文件
    total_files = len(my_manifest)
    sent_files = 0
    for relpath in my_manifest:
        try:
            send_file_by_rel(sock, base_dir, relpath)
            sent_files += 1
            log_func('Progress: %d/%d files sent - %s', sent_files, total_files, relpath)
        except Exception as e:
            log_func('Failed to send file %s: %s', relpath, e)
    
    # 发送完成信号
    send_json(sock, {'type': 'done_sending'})
    log_func('All files sent successfully (%d files)', sent_files)

def handle_unidirectional_receive(sock, base_dir, log_callback=None):
    """接收方逻辑：接收所有来自发送方的文件"""
    base_dir = Path(base_dir)
    log_func = log_callback or logging.info
    
    # 接收模式标识
    msg = recv_json(sock)
    if not msg or msg.get('type') != 'mode' or msg.get('mode') != 'send':
        log_func('Expected send mode from sender, got: %s', msg)
        return
    
    # 接收文件清单
    msg = recv_json(sock)
    if not msg or msg.get('type') != 'manifest':
        log_func('Expected manifest from sender, got: %s', msg)
        return
    
    sender_manifest = msg['manifest']
    log_func('Received manifest with %d files from sender', len(sender_manifest))
    
    # 发送确认信号
    send_json(sock, {'type': 'ready'})
    
    # 接收所有文件
    received_files = 0
    total_files = len(sender_manifest)
    
    while True:
        msg = recv_json(sock)
        if not msg:
            break
            
        if msg.get('type') == 'file':
            receive_file(sock, base_dir, msg)
            received_files += 1
            log_func('Progress: %d/%d files received - %s', received_files, total_files, msg['path'])
        elif msg.get('type') == 'done_sending':
            log_func('Sender finished sending all files')
            break
        else:
            log_func('Unexpected message type: %s', msg.get('type'))
    
    log_func('All files received successfully (%d files)', received_files)

# --- 双向同步逻辑 ---

def handle_connection(sock, base_dir, log_callback=None):
    """Exchange manifests and then mutually request/send files."""
    base_dir = Path(base_dir)
    log_func = log_callback or logging.info
    
    incoming_done = threading.Event()
    outgoing_done = threading.Event()
    peer_manifest = {}
    my_manifest = build_manifest(base_dir)
    log_func('Built local manifest with %d files', len(my_manifest))

    # send my manifest
    send_json(sock, {'type': 'manifest', 'manifest': my_manifest})
    log_func('Sent local manifest')

    # receive peer manifest
    msg = recv_json(sock)
    if not msg or msg.get('type') != 'manifest':
        log_func('Expected manifest from peer, got: %s', msg)
        return
    peer_manifest = msg['manifest']
    log_func('Received peer manifest with %d files', len(peer_manifest))

    # compute want list
    want = []
    for rel, meta in peer_manifest.items():
        if rel not in my_manifest:
            want.append(rel)
        else:
            my_meta = my_manifest[rel]
            if my_meta['sha256'] != meta['sha256'] and meta['mtime'] > my_meta['mtime']:
                want.append(rel)
    log_func('Will request %d files from peer', len(want))

    will_send = []
    for rel, meta in my_manifest.items():
        if rel not in peer_manifest:
            will_send.append(rel)
        else:
            peer_meta = peer_manifest[rel]
            if peer_meta['sha256'] != meta['sha256'] and my_manifest[rel]['mtime'] > peer_meta['mtime']:
                will_send.append(rel)
    log_func('Peer may request up to %d files from us', len(will_send))

    def receiver():
        nonlocal incoming_done
        try:
            while True:
                m = recv_json(sock)
                if m is None:
                    log_func('Connection closed by peer')
                    break
                t = m.get('type')
                if t == 'want':
                    files = m.get('files', [])
                    log_func('Peer requested %d files', len(files))
                    for f in files:
                        try:
                            send_file_by_rel(sock, base_dir, f)
                            log_func('Sent file to peer: %s', f)
                        except Exception as e:
                            log_func('Failed to send file %s: %s', f, e)
                    send_json(sock, {'type': 'done_sending'})
                elif t == 'file':
                    receive_file(sock, base_dir, m)
                    log_func('Received file from peer: %s', m['path'])
                elif t == 'done_sending':
                    log_func('Peer finished sending requested files')
                    incoming_done.set()
                else:
                    log_func('Unknown message type: %s', t)
        except Exception as e:
            log_func('Receiver error: %s', e)
        finally:
            incoming_done.set()

    recv_thread = threading.Thread(target=receiver, daemon=True)
    recv_thread.start()

    send_json(sock, {'type': 'want', 'files': want})
    log_func('Sent want list to peer')

    log_func('Waiting for peer to send files we requested...')
    incoming_done.wait(timeout=300)
    log_func('Incoming phase done (or timeout)')
    
    try:
        sock.shutdown(socket.SHUT_RDWR)
    except Exception:
        pass
    sock.close()


def run_listen(port, base_dir, log_callback=None, bind='0.0.0.0'):
    log_func = log_callback or logging.info
    log_func('Listening on %s:%d', bind, port)
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        s.bind((bind, port))
        s.listen(1)
        conn, addr = s.accept()
        log_func('Accepted connection from %s:%d', addr[0], addr[1])
        with conn:
            handle_connection(conn, base_dir, log_callback)


def run_connect(host, port, base_dir, log_callback=None):
    log_func = log_callback or logging.info
    log_func('Connecting to %s:%d ...', host, port)
    with socket.create_connection((host, port), timeout=30) as sock:
        log_func('Connected to %s:%d', host, port)
        handle_connection(sock, base_dir, log_callback)


def run_send(port, base_dir, log_callback=None, bind='0.0.0.0'):
    """运行发送方模式"""
    log_func = log_callback or logging.info
    log_func('Starting as sender on %s:%d', bind, port)
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        s.bind((bind, port))
        s.listen(1)
        conn, addr = s.accept()
        log_func('Accepted connection from receiver %s:%d', addr[0], addr[1])
        with conn:
            handle_unidirectional_send(conn, base_dir, log_callback)


def run_receive(host, port, base_dir, log_callback=None):
    """运行接收方模式"""
    log_func = log_callback or logging.info
    log_func('Connecting to sender %s:%d ...', host, port)
    with socket.create_connection((host, port), timeout=30) as sock:
        log_func('Connected to sender %s:%d', host, port)
        handle_unidirectional_receive(sock, base_dir, log_callback)


def main():
    parser = argparse.ArgumentParser(description='LAN folder sync (support bidirectional and unidirectional)')
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument('--listen', action='store_true', help='listen for a peer (bidirectional)')
    group.add_argument('--connect', metavar='HOST', help='connect to a listening peer (bidirectional)')
    group.add_argument('--send', action='store_true', help='run as sender (unidirectional)')
    group.add_argument('--receive', metavar='HOST', help='connect to a sender (unidirectional)')
    parser.add_argument('--port', type=int, default=9000, help='port to listen/connect (default: 9000)')
    parser.add_argument('--bind', default='0.0.0.0', help='bind address for listen (default: 0.0.0.0)')
    args = parser.parse_args()
    cwd = os.getcwd()
    logging.info('Working dir: %s', cwd)
    
    if args.listen:
        run_listen(args.port, cwd, bind=args.bind)
    elif args.connect:
        run_connect(args.connect, args.port, cwd)
    elif args.send:
        run_send(args.port, cwd, bind=args.bind)
    elif args.receive:
        run_receive(args.receive, args.port, cwd)

if __name__ == '__main__':
    main()