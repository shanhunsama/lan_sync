"""发送文件标签页模块"""

import os
import threading
# 在文件顶部添加导入路径设置
import sys
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

# 然后更新导入语句
from core.network_services import run_send
from PyQt5 import QtWidgets, QtCore
import socket

import sync
from config_manager import ConfigManager
from utils import LogMixin, browse_folder


class SendTab(QtWidgets.QWidget, LogMixin):
    """发送文件模式标签页 - 单向发送文件到接收方"""
    
    def __init__(self):
        super().__init__()
        self.sync_thread = None
        self.sync_running = False
        self._build_ui()
    
    def _build_ui(self):
        """构建发送文件界面"""
        layout = QtWidgets.QVBoxLayout(self)
        
        # === 发送文件夹设置 ===
        folder_group = QtWidgets.QGroupBox("发送文件夹设置")
        folder_layout = QtWidgets.QHBoxLayout(folder_group)
        
        self.folder_edit = QtWidgets.QLineEdit(str(Path.cwd()))
        self.folder_edit.setPlaceholderText("选择要发送的文件夹")
        
        btn_browse = QtWidgets.QPushButton('浏览文件夹')
        btn_browse.clicked.connect(self.on_browse)
        
        folder_layout.addWidget(QtWidgets.QLabel('发送文件夹:'))
        folder_layout.addWidget(self.folder_edit, 1)
        folder_layout.addWidget(btn_browse)
        layout.addWidget(folder_group)
        
        # === 网络设置 ===
        network_group = QtWidgets.QGroupBox("网络设置")
        form_layout = QtWidgets.QFormLayout(network_group)
        
        self.host_edit = QtWidgets.QLineEdit('192.168.1.100')
        self.host_edit.setPlaceholderText("接收方设备的IP地址")
        self.port_edit = QtWidgets.QLineEdit('9000')
        self.port_edit.setToolTip("接收方服务的端口号")
        
        form_layout.addRow('接收方地址:', self.host_edit)
        form_layout.addRow('端口号:', self.port_edit)
        layout.addWidget(network_group)
        
        # === 控制按钮 ===
        control_group = QtWidgets.QGroupBox("操作控制")
        control_layout = QtWidgets.QHBoxLayout(control_group)
        
        self.btn_start = QtWidgets.QPushButton('开始发送')
        self.btn_start.clicked.connect(self.on_start)
        self.btn_start.setToolTip("连接到接收方并开始发送文件")
        
        self.btn_stop = QtWidgets.QPushButton('停止')
        self.btn_stop.clicked.connect(self.on_stop)
        self.btn_stop.setEnabled(False)
        
        control_layout.addWidget(self.btn_start)
        control_layout.addWidget(self.btn_stop)
        control_layout.addStretch(1)
        layout.addWidget(control_group)
        
        # === 日志显示 ===
        log_group = QtWidgets.QGroupBox("发送日志")
        log_layout = QtWidgets.QVBoxLayout(log_group)
        
        self.log = QtWidgets.QPlainTextEdit()
        self.log.setReadOnly(True)
        
        btn_clear = QtWidgets.QPushButton('清空日志')
        btn_clear.clicked.connect(self.on_clear_log)
        
        log_layout.addWidget(self.log, 1)
        log_layout.addWidget(btn_clear)
        layout.addWidget(log_group, 1)
        
        layout.addStretch(1)
    
    def on_browse(self):
        current_dir = self.folder_edit.text() or str(Path.cwd())
        selected_dir = QtWidgets.QFileDialog.getExistingDirectory(
            self, '选择发送文件夹', current_dir)
        if selected_dir:
            self.folder_edit.setText(selected_dir)
    
    def on_clear_log(self):
        self.log.clear()
    
    def on_start(self):
        if self.sync_running:
            return
        
        folder = self.folder_edit.text().strip()
        if not folder:
            QtWidgets.QMessageBox.warning(self, '错误', '请选择要发送的文件夹')
            return
        if not os.path.exists(folder):
            QtWidgets.QMessageBox.warning(self, '错误', '选择的文件夹不存在')
            return
        
        host = self.host_edit.text().strip()
        if not host:
            QtWidgets.QMessageBox.warning(self, '错误', '请输入接收方地址')
            return
        
        port = self.port_edit.text().strip()
        if not port.isdigit():
            QtWidgets.QMessageBox.warning(self, '错误', '端口号必须是数字')
            return
        port = int(port)
        
        self.append_log('启动发送模式...')
        self.append_log(f'正在连接到接收方 {host}:{port}...')
        self.sync_running = True
        self.btn_start.setEnabled(False)
        self.btn_stop.setEnabled(True)
        
        def run_sync():
            try:
                sync.run_send(host, port, folder, self.append_log)
            except Exception as e:
                self.append_log(f'发送错误: {e}')
            finally:
                self.sync_running = False
                self.append_log('发送完成')
                QtCore.QMetaObject.invokeMethod(
                    self, "on_sync_finished", QtCore.Qt.QueuedConnection)
        
        self.sync_thread = threading.Thread(target=run_sync, daemon=True)
        self.sync_thread.start()
    
    @QtCore.pyqtSlot()
    def on_sync_finished(self):
        self.btn_start.setEnabled(True)
        self.btn_stop.setEnabled(False)
    
    def on_stop(self):
        if self.sync_running:
            self.append_log('正在停止发送...')
            self.sync_running = False
            self.btn_start.setEnabled(True)
            self.btn_stop.setEnabled(False)