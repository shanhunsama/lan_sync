"""优化的文件传输模块 - 包含全面的性能优化"""

import os
import struct
import logging
import mmap
import zlib
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed

from .helpers import (
    recvn, send_json, get_chunk_size, get_socket_buffer_size, 
    should_disable_nagle, should_use_memory_mapping, 
    should_use_stream_protocol, calculate_optimal_chunk_size,
    calculate_optimal_threads, should_enable_compression,
    get_compression_threshold
)

class OptimizedFileTransfer:
    """优化的文件传输类"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
    
    def send_file_optimized(self, sock, base_dir, relpath):
        """优化的文件发送方法"""
        path = Path(base_dir) / Path(relpath)
        file_size = path.stat().st_size
        
        # 计算最优参数
        optimal_chunk_size = calculate_optimal_chunk_size(file_size)
        optimal_threads = calculate_optimal_threads(file_size)
        
        header = {
            'type': 'file', 
            'path': relpath, 
            'size': file_size,
            'chunk_size': optimal_chunk_size,
            'compressed': False
        }
        
        # 检查是否需要压缩
        if should_enable_compression() and file_size > get_compression_threshold():
            header['compressed'] = True
        
        send_json(sock, header)
        
        # 根据文件大小选择传输策略
        if file_size < 10 * 1024 * 1024:  # 小文件使用单线程
            self._send_single_thread(sock, path, file_size, optimal_chunk_size, header['compressed'])
        else:  # 大文件使用多线程
            self._send_multi_thread(sock, path, file_size, optimal_chunk_size, optimal_threads, header['compressed'])
        
        self.logger.info('Optimized sent file: %s (%d bytes, chunks: %d, threads: %d)', 
                        relpath, file_size, optimal_chunk_size, optimal_threads)
    
    def _send_single_thread(self, sock, path, file_size, chunk_size, compressed):
        """单线程发送"""
        if should_use_memory_mapping() and file_size > 0:
            # 使用内存映射优化
            self._send_with_memory_mapping(sock, path, file_size, chunk_size, compressed)
        else:
            # 传统文件读取
            self._send_with_file_io(sock, path, file_size, chunk_size, compressed)
    
    def _send_multi_thread(self, sock, path, file_size, chunk_size, thread_count, compressed):
        """多线程发送"""
        chunks = []
        offset = 0
        
        # 计算块信息
        while offset < file_size:
            current_chunk_size = min(chunk_size, file_size - offset)
            chunks.append((offset, current_chunk_size))
            offset += current_chunk_size
        
        # 使用线程池并行发送
        with ThreadPoolExecutor(max_workers=thread_count) as executor:
            futures = []
            for chunk_offset, chunk_size in chunks:
                future = executor.submit(
                    self._send_chunk, sock, path, chunk_offset, chunk_size, compressed
                )
                futures.append(future)
            
            # 等待所有块发送完成
            for future in as_completed(futures):
                try:
                    future.result()
                except Exception as e:
                    self.logger.error('Error sending chunk: %s', e)
                    raise
    
    def _send_chunk(self, sock, path, offset, chunk_size, compressed):
        """发送单个块"""
        with open(path, 'rb') as f:
            f.seek(offset)
            chunk_data = f.read(chunk_size)
            
            if compressed:
                chunk_data = zlib.compress(chunk_data, level=1)  # 快速压缩
            
            # 流式协议：只发送数据，不发送长度前缀
            if should_use_stream_protocol():
                sock.sendall(chunk_data)
            else:
                # 传统协议：长度前缀 + 数据
                sock.sendall(struct.pack('>I', len(chunk_data)))
                sock.sendall(chunk_data)
    
    def _send_with_memory_mapping(self, sock, path, file_size, chunk_size, compressed):
        """使用内存映射发送文件"""
        with open(path, 'rb') as f:
            with mmap.mmap(f.fileno(), file_size, access=mmap.ACCESS_READ) as mm:
                offset = 0
                while offset < file_size:
                    current_chunk_size = min(chunk_size, file_size - offset)
                    chunk_data = mm[offset:offset + current_chunk_size]
                    
                    if compressed:
                        chunk_data = zlib.compress(chunk_data, level=1)
                    
                    if should_use_stream_protocol():
                        sock.sendall(chunk_data)
                    else:
                        sock.sendall(struct.pack('>I', len(chunk_data)))
                        sock.sendall(chunk_data)
                    
                    offset += current_chunk_size
    
    def _send_with_file_io(self, sock, path, file_size, chunk_size, compressed):
        """使用文件IO发送文件"""
        with open(path, 'rb') as f:
            while True:
                chunk_data = f.read(chunk_size)
                if not chunk_data:
                    break
                
                if compressed:
                    chunk_data = zlib.compress(chunk_data, level=1)
                
                if should_use_stream_protocol():
                    sock.sendall(chunk_data)
                else:
                    sock.sendall(struct.pack('>I', len(chunk_data)))
                    sock.sendall(chunk_data)
    
    def receive_file_optimized(self, sock, base_dir, header):
        """优化的文件接收方法"""
        rel = header['path']
        file_size = header['size']
        chunk_size = header.get('chunk_size', get_chunk_size())
        compressed = header.get('compressed', False)
        
        rel_path = Path(rel)
        if rel_path.is_absolute() or '..' in rel_path.parts:
            self.logger.error('Rejected unsafe path from peer: %s', rel)
            self._consume_file_stream(sock, chunk_size, compressed)
            return
        
        out_path = Path(base_dir) / rel_path
        out_path.parent.mkdir(parents=True, exist_ok=True)
        
        optimal_threads = calculate_optimal_threads(file_size)
        
        if file_size < 10 * 1024 * 1024:
            self._receive_single_thread(sock, out_path, file_size, chunk_size, compressed)
        else:
            self._receive_multi_thread(sock, out_path, file_size, chunk_size, optimal_threads, compressed)
        
        self.logger.info('Optimized received file: %s (%d bytes)', rel, file_size)
    
    def _receive_single_thread(self, sock, out_path, file_size, chunk_size, compressed):
        """单线程接收"""
        received = 0
        temp_path = str(out_path) + '.tmp'
        
        with open(temp_path, 'wb') as f:
            while received < file_size:
                if should_use_stream_protocol():
                    # 流式协议接收
                    remaining = file_size - received
                    current_chunk_size = min(chunk_size, remaining)
                    chunk_data = recvn(sock, current_chunk_size)
                else:
                    # 传统协议接收
                    ln_b = recvn(sock, 4)
                    if not ln_b:
                        raise ConnectionError('Unexpected EOF during file transfer')
                    (ln,) = struct.unpack('>I', ln_b)
                    if ln == 0:
                        break
                    chunk_data = recvn(sock, ln)
                
                if not chunk_data:
                    raise ConnectionError('Unexpected EOF during file transfer')
                
                if compressed:
                    chunk_data = zlib.decompress(chunk_data)
                
                f.write(chunk_data)
                received += len(chunk_data)
        
        os.replace(temp_path, out_path)
    
    def _receive_multi_thread(self, sock, out_path, file_size, chunk_size, thread_count, compressed):
        """多线程接收（需要协议支持）"""
        # 简化实现：使用单线程接收大文件
        self._receive_single_thread(sock, out_path, file_size, chunk_size, compressed)
    
    def _consume_file_stream(self, sock, chunk_size, compressed):
        """消耗文件流（用于拒绝不安全路径时）"""
        if should_use_stream_protocol():
            # 流式协议需要特殊处理
            raise NotImplementedError("Stream protocol consumption not implemented")
        else:
            # 传统协议消耗
            while True:
                ln_b = recvn(sock, 4)
                if not ln_b:
                    return
                (ln,) = struct.unpack('>I', ln_b)
                if ln == 0:
                    break
                chunk = recvn(sock, ln)
                if not chunk:
                    return

# 向后兼容的函数
def send_file_by_rel_optimized(sock, base_dir, relpath):
    """优化的文件发送函数（向后兼容）"""
    transfer = OptimizedFileTransfer()
    return transfer.send_file_optimized(sock, base_dir, relpath)

def receive_file_optimized(sock, base_dir, header):
    """优化的文件接收函数（向后兼容）"""
    transfer = OptimizedFileTransfer()
    return transfer.receive_file_optimized(sock, base_dir, header)