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
import logging
import argparse
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from core import run_listen, run_connect, run_send, run_receive


def main():
    # 配置日志
    if not logging.getLogger().handlers:
        logging.basicConfig(level=logging.INFO, format='[%(asctime)s] %(message)s')
    
    parser = argparse.ArgumentParser(description='LAN folder sync (support bidirectional and unidirectional)')
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument('--listen', action='store_true', help='listen for a peer (bidirectional)')
    group.add_argument('--connect', metavar='HOST', help='connect to a listening peer (bidirectional)')
    group.add_argument('--send', metavar='HOST', help='run as sender (unidirectional)')
    group.add_argument('--receive', action='store_true', help='run as receiver (unidirectional)')
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
        run_send(args.send, args.port, cwd)  # args.send now contains the host
    elif args.receive:
        run_receive(args.port, cwd, bind=args.bind)


if __name__ == '__main__':
    main()