"""单向传输模块（发送方 -> 接收方）"""

import logging
from pathlib import Path

from .helpers import send_json, recv_json, build_manifest
from .file_transfer import send_file_by_rel, receive_file


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