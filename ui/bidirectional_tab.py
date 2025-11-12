"""双向同步标签页模块"""

import os
import threading
import sys
from pathlib import Path
from PyQt5 import QtWidgets, QtCore
import socket

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

import sync
from config_manager import ConfigManager
from utils import LogMixin, browse_folder


class BidirectionalTab(QtWidgets.QWidget, LogMixin):
    """双向同步模式标签页 - 支持监听和连接两种方式"""
    
    def __init__(self):
        super().__init__()
        self.sync_thread = None
        self.sync_running = False
        self._build_ui()
    
    def _build_ui(self):
        """构建双向同步界面"""
        layout = QtWidgets.QVBoxLayout(self)
        
        # === 文件夹选择区域 ===
        folder_group = QtWidgets.QGroupBox("同步文件夹设置")
        folder_layout = QtWidgets.QHBoxLayout(folder_group)
        
        # 文件夹路径输入框
        self.folder_edit = QtWidgets.QLineEdit(str(Path.cwd()))
        self.folder_edit.setPlaceholderText("请选择要同步的文件夹路径")
        
        # 浏览按钮
        btn_browse = QtWidgets.QPushButton('浏览文件夹')
        btn_browse.clicked.connect(self.on_browse)
        
        folder_layout.addWidget(QtWidgets.QLabel('同步文件夹:'))
        folder_layout.addWidget(self.folder_edit, 1)
        folder_layout.addWidget(btn_browse)
        layout.addWidget(folder_group)
        
        # === 模式选择区域 ===
        mode_group = QtWidgets.QGroupBox("同步模式选择")
        mode_layout = QtWidgets.QVBoxLayout(mode_group)
        
        # 模式选择按钮组
        self.mode_group = QtWidgets.QButtonGroup(self)
        
        # 监听模式单选按钮
        self.rb_listen = QtWidgets.QRadioButton('监听模式 (作为服务器)')
        self.rb_listen.setChecked(True)
        self.rb_listen.setToolTip("在此设备上启动服务，等待其他设备连接进行双向同步")
        
        # 连接模式单选按钮
        self.rb_connect = QtWidgets.QRadioButton('连接模式 (连接到服务器)')
        self.rb_connect.setToolTip("连接到其他设备的监听服务进行双向同步")
        
        self.mode_group.addButton(self.rb_listen)
        self.mode_group.addButton(self.rb_connect)
        
        mode_layout.addWidget(self.rb_listen)
        mode_layout.addWidget(self.rb_connect)
        layout.addWidget(mode_group)
        
        # === 网络设置区域 ===
        network_group = QtWidgets.QGroupBox("网络设置")
        form_layout = QtWidgets.QFormLayout(network_group)
        
        # 主机地址输入框
        self.host_edit = QtWidgets.QLineEdit('192.168.1.100')
        self.host_edit.setPlaceholderText("请输入目标设备的IP地址")
        self.host_edit.setToolTip("要连接的设备IP地址，如: 192.168.1.100")
        
        # 端口号输入框
        self.port_edit = QtWidgets.QLineEdit('9000')
        self.port_edit.setToolTip("同步服务使用的端口号，默认9000")
        
        form_layout.addRow('目标主机地址:', self.host_edit)
        form_layout.addRow('端口号:', self.port_edit)
        layout.addWidget(network_group)
        
        # === 控制按钮区域 ===
        control_group = QtWidgets.QGroupBox("操作控制")
        control_layout = QtWidgets.QHBoxLayout(control_group)
        
        # 开始按钮
        self.btn_start = QtWidgets.QPushButton('开始同步')
        self.btn_start.clicked.connect(self.on_start)
        self.btn_start.setToolTip("开始双向文件同步过程")
        
        # 停止按钮
        self.btn_stop = QtWidgets.QPushButton('停止')
        self.btn_stop.clicked.connect(self.on_stop)
        self.btn_stop.setEnabled(False)
        self.btn_stop.setToolTip("停止当前的同步过程")
        
        control_layout.addWidget(self.btn_start)
        control_layout.addWidget(self.btn_stop)
        control_layout.addStretch(1)
        layout.addWidget(control_group)
        
        # === 日志显示区域 ===
        log_group = QtWidgets.QGroupBox("同步日志")
        log_layout = QtWidgets.QVBoxLayout(log_group)
        
        # 日志显示文本框
        self.log = QtWidgets.QPlainTextEdit()
        self.log.setReadOnly(True)
        self.log.setPlaceholderText("同步日志将显示在这里...")
        
        # 清空日志按钮
        btn_clear = QtWidgets.QPushButton('清空日志')
        btn_clear.clicked.connect(self.on_clear_log)
        
        log_layout.addWidget(self.log, 1)
        log_layout.addWidget(btn_clear)
        layout.addWidget(log_group, 1)
        
        layout.addStretch(1)
    
    def on_browse(self):
        """浏览文件夹按钮点击事件"""
        selected_dir = browse_folder(self, self.folder_edit.text())
        if selected_dir:
            self.folder_edit.setText(selected_dir)
    
    def on_clear_log(self):
        """清空日志按钮点击事件"""
        self.log.clear()
    
    def on_start(self):
        """开始同步按钮点击事件"""
        if self.sync_running:
            return
        
        # 验证文件夹路径
        folder = self.folder_edit.text().strip()
        if not folder:
            QtWidgets.QMessageBox.warning(self, '错误', '请选择要同步的文件夹')
            return
        if not os.path.exists(folder):
            QtWidgets.QMessageBox.warning(self, '错误', '选择的文件夹不存在')
            return
        
        # 验证端口号
        port = self.port_edit.text().strip()
        if not port.isdigit():
            QtWidgets.QMessageBox.warning(self, '错误', '端口号必须是数字')
            return
        port = int(port)
        
        # 验证主机地址（连接模式下）
        if self.rb_connect.isChecked():
            host = self.host_edit.text().strip()
            if not host:
                QtWidgets.QMessageBox.warning(self, '错误', '请输入要连接的主机地址')
                return
        
        # 确定模式并启动同步
        mode = 'listen' if self.rb_listen.isChecked() else 'connect'
        host = self.host_edit.text().strip() if self.rb_connect.isChecked() else ''
        
        self.append_log(f'启动{mode}模式...')
        self.sync_running = True
        self.btn_start.setEnabled(False)
        self.btn_stop.setEnabled(True)
        
        # 在后台线程中运行同步
        def run_sync():
            try:
                if mode == 'listen':
                    sync.run_listen(port, folder, self.append_log)
                else:
                    sync.run_connect(host, port, folder, self.append_log)
            except Exception as e:
                self.append_log(f'同步错误: {e}')
            finally:
                self.sync_running = False
                self.append_log('同步完成')
                QtCore.QMetaObject.invokeMethod(
                    self, "on_sync_finished", QtCore.Qt.QueuedConnection)
        
        self.sync_thread = threading.Thread(target=run_sync, daemon=True)
        self.sync_thread.start()
    
    @QtCore.pyqtSlot()
    def on_sync_finished(self):
        """同步完成后的UI更新"""
        self.btn_start.setEnabled(True)
        self.btn_stop.setEnabled(False)
    
    def on_stop(self):
        """停止同步按钮点击事件"""
        if self.sync_running:
            self.append_log('正在停止同步...')
            self.sync_running = False
            self.btn_start.setEnabled(True)
            self.btn_stop.setEnabled(False)