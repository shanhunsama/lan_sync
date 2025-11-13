"""双向同步模块"""

import socket
import threading
import logging
from pathlib import Path

from .helpers import send_json, recv_json, build_manifest
from .file_transfer import send_file_by_rel, receive_file


def handle_connection(sock, base_dir, log_callback=None):
    """交换清单并相互请求/发送文件"""
    base_dir = Path(base_dir)
    log_func = log_callback or logging.info
    
    incoming_done = threading.Event()
    outgoing_done = threading.Event()
    peer_manifest = {}
    my_manifest = build_manifest(base_dir)
    log_func('Built local manifest with %d files', len(my_manifest))

    # 发送我的清单
    send_json(sock, {'type': 'manifest', 'manifest': my_manifest})
    log_func('Sent local manifest')

    # 接收对等方清单
    msg = recv_json(sock)
    if not msg or msg.get('type') != 'manifest':
        log_func('Expected manifest from peer, got: %s', msg)
        return
    peer_manifest = msg['manifest']
    log_func('Received peer manifest with %d files', len(peer_manifest))

    # 计算需求列表
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
    """运行监听模式"""
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
    """运行连接模式"""
    log_func = log_callback or logging.info
    log_func('Connecting to %s:%d ...', host, port)
    with socket.create_connection((host, port), timeout=30) as sock:
        log_func('Connected to %s:%d', host, port)
        handle_connection(sock, base_dir, log_callback)