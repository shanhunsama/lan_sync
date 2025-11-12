"""
简单的局域网双向一次性同步工具

运行方式（示例）:
  监听方（机器 A）:
    python sync.py --listen --port 9000

  连接方（机器 B）:
    python sync.py --connect 192.168.1.100 --port 9000

在当前工作目录下运行脚本（脚本会同步该目录及子目录）。

协议概述：
- 双方交换清单（relative path, size, mtime, sha256）
- 双方各生成想要从对方获取的文件列表（remote newer 或 本地无）并发送请求
- 双方并行处理来自对方的请求（对方会发送文件）并发送自己需要的文件
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


# --- main sync logic ---

def handle_connection(sock, base_dir):
    """Exchange manifests and then mutually request/send files.

    Protocol steps:
    1. send manifest
    2. recv peer manifest
    3. compute want_list (files I want from peer)
    4. send {'type':'want','files':[...]} message
    5. concurrently process incoming messages until both sides signal done
    """
    base_dir = Path(base_dir)
    # start receiver thread that will process incoming messages (requests and file transfers)
    incoming_done = threading.Event()
    outgoing_done = threading.Event()
    peer_manifest = {}
    my_manifest = build_manifest(base_dir)
    logging.info('Built local manifest with %d files', len(my_manifest))

    # send my manifest
    send_json(sock, {'type': 'manifest', 'manifest': my_manifest})
    logging.info('Sent local manifest')

    # receive peer manifest
    msg = recv_json(sock)
    if not msg or msg.get('type') != 'manifest':
        logging.error('Expected manifest from peer, got: %s', msg)
        return
    peer_manifest = msg['manifest']
    logging.info('Received peer manifest with %d files', len(peer_manifest))

    # compute want list: files that peer has and (we don't have OR peer mtime > our mtime and sha differ)
    want = []
    for rel, meta in peer_manifest.items():
        if rel not in my_manifest:
            want.append(rel)
        else:
            my_meta = my_manifest[rel]
            if my_meta['sha256'] != meta['sha256'] and meta['mtime'] > my_meta['mtime']:
                want.append(rel)
    logging.info('Will request %d files from peer', len(want))

    # Similarly compute will_send list (peer might want some of our files)
    will_send = []
    for rel, meta in my_manifest.items():
        if rel not in peer_manifest:
            will_send.append(rel)
        else:
            peer_meta = peer_manifest[rel]
            if peer_meta['sha256'] != meta['sha256'] and my_manifest[rel]['mtime'] > peer_meta['mtime']:
                will_send.append(rel)
    logging.info('Peer may request up to %d files from us', len(will_send))

    # structures for coordinating
    recv_lock = threading.Lock()
    # When receiver sees a 'want' from peer, it will queue files to send

    def receiver():
        nonlocal incoming_done
        try:
            while True:
                m = recv_json(sock)
                if m is None:
                    logging.info('Connection closed by peer')
                    break
                t = m.get('type')
                if t == 'want':
                    files = m.get('files', [])
                    logging.info('Peer requested %d files', len(files))
                    for f in files:
                        # send each file
                        try:
                            send_file_by_rel(sock, base_dir, f)
                        except Exception as e:
                            logging.error('Failed to send file %s: %s', f, e)
                    # after sending requested files, send a 'done_sending' marker
                    send_json(sock, {'type': 'done_sending'})
                elif t == 'file':
                    # we got a file header, now receive file bytes
                    receive_file(sock, base_dir, m)
                elif t == 'done_sending':
                    logging.info('Peer finished sending requested files')
                    # mark incoming finished
                    incoming_done.set()
                    # but keep loop in case peer sends more (rare)
                else:
                    logging.warning('Unknown message type: %s', t)
        except Exception as e:
            logging.error('Receiver error: %s', e)
        finally:
            incoming_done.set()

    recv_thread = threading.Thread(target=receiver, daemon=True)
    recv_thread.start()

    # send our want list
    send_json(sock, {'type': 'want', 'files': want})
    logging.info('Sent want list to peer')

    # Now process will_send: but we actually wait for peer to request; our receiver will handle requests
    # Wait until both sides signal done (incoming_done set when peer sent 'done_sending')
    # We also expect to receive files we requested; the peer will send 'done_sending' when done
    # Block until incoming_done is set
    logging.info('Waiting for peer to send files we requested...')
    # Also set a timeout guard: if want is empty, peer may not send anything and will send 'done_sending' quickly
    incoming_done.wait(timeout=300)
    logging.info('Incoming phase done (or timeout)')
    # Close socket politely
    try:
        sock.shutdown(socket.SHUT_RDWR)
    except Exception:
        pass
    sock.close()


def run_listen(port, base_dir, bind='0.0.0.0'):
    logging.info('Listening on %s:%d', bind, port)
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        s.bind((bind, port))
        s.listen(1)
        conn, addr = s.accept()
        logging.info('Accepted connection from %s:%d', addr[0], addr[1])
        with conn:
            handle_connection(conn, base_dir)


def run_connect(host, port, base_dir):
    logging.info('Connecting to %s:%d ...', host, port)
    with socket.create_connection((host, port), timeout=30) as sock:
        logging.info('Connected to %s:%d', host, port)
        handle_connection(sock, base_dir)


def main():
    parser = argparse.ArgumentParser(description='LAN folder sync (one-shot, bidirectional)')
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument('--listen', action='store_true', help='listen for a peer')
    group.add_argument('--connect', metavar='HOST', help='connect to a listening peer')
    parser.add_argument('--port', type=int, default=9000, help='port to listen/connect (default: 9000)')
    parser.add_argument('--bind', default='0.0.0.0', help='bind address for listen (default: 0.0.0.0)')
    args = parser.parse_args()
    cwd = os.getcwd()
    logging.info('Working dir: %s', cwd)
    if args.listen:
        run_listen(args.port, cwd, bind=args.bind)
    else:
        run_connect(args.connect, args.port, cwd)

if __name__ == '__main__':
    main()
