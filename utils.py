"""工具函数模块 - 包含通用的工具函数"""

import socket
from PyQt5 import QtCore, QtWidgets
from pathlib import Path


def get_local_ip():
    """获取本机IP地址"""
    try:
        # 创建一个临时socket连接来获取本机IP
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        local_ip = s.getsockname()[0]
        s.close()
        return local_ip
    except:
        return "无法获取IP地址"


def browse_folder(parent_widget, current_path=None):
    """浏览文件夹对话框"""
    current_dir = current_path or str(Path.cwd())
    selected_dir = QtWidgets.QFileDialog.getExistingDirectory(
        parent_widget, '选择文件夹', current_dir)
    return selected_dir


class LogMixin:
    """日志混入类，提供通用的日志功能"""
    
    def append_log(self, *args):
        """处理日志输出，支持格式化参数"""
        if len(args) == 0:
            return
            
        # 如果只有一个参数，直接使用
        if len(args) == 1:
            text = str(args[0])
        # 如果有多个参数，第一个是格式字符串，其余是参数
        else:
            try:
                text = args[0] % args[1:]
            except:
                # 如果格式化失败，将所有参数连接起来
                text = ' '.join(str(arg) for arg in args)
        
        QtCore.QMetaObject.invokeMethod(
            self, "_safe_append_log", QtCore.Qt.QueuedConnection,
            QtCore.Q_ARG(str, text)
        )
    
    @QtCore.pyqtSlot(str)
    def _safe_append_log(self, text):
        """在主线程中安全地添加日志"""
        if hasattr(self, 'log'):
            self.log.appendPlainText(text)
            # 自动滚动到底部
            scrollbar = self.log.verticalScrollBar()
            scrollbar.setValue(scrollbar.maximum())