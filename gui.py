#!/usr/bin/env python
"""LAN文件同步工具 - 图形界面

功能特性:
- 双向同步模式: 监听(Listen)和连接(Connect)
- 单向传输模式: 发送(Send)和接收(Receive)
- 文件夹选择功能
- 实时日志显示
- 线程安全的UI操作

使用方法:
    python gui.py

依赖: PyQt5 (在requirements.txt中列出)
"""

import sys
import os
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from PyQt5 import QtWidgets
from ui.main_window import MainWindow


def main():
    """主函数 - 启动GUI应用程序"""
    app = QtWidgets.QApplication(sys.argv)
    
    # 设置应用程序信息
    app.setApplicationName("LAN文件同步工具")
    app.setApplicationVersion("1.0.0")
    
    # 创建并显示主窗口
    window = MainWindow()
    window.show()
    
    # 运行应用程序
    sys.exit(app.exec_())


if __name__ == '__main__':
    main()