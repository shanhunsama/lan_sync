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
import threading
import socket
from pathlib import Path
from PyQt5 import QtWidgets, QtCore, QtGui

# 导入同步模块
try:
    import sync
except ImportError:
    # 打包环境下的导入处理
    import sys
    from pathlib import Path
    current_dir = Path(__file__).parent
    if str(current_dir) not in sys.path:
        sys.path.insert(0, str(current_dir))
    import sync


class MainWindow(QtWidgets.QMainWindow):
    """主窗口类，包含模式选择标签页"""
    
    def __init__(self):
        super().__init__()
        self.setWindowTitle('LAN文件同步工具')
        self.setWindowIcon(QtGui.QIcon())  # 可以添加图标
        self.resize(800, 600)
        
        self._build_ui()
    
    def _build_ui(self):
        """构建主界面"""
        # 创建中央部件
        central_widget = QtWidgets.QWidget()
        self.setCentralWidget(central_widget)
        
        # 主布局
        main_layout = QtWidgets.QVBoxLayout(central_widget)
        
        # 创建标签页控件
        self.tab_widget = QtWidgets.QTabWidget()
        
        # 添加各个模式标签页
        self.bidirectional_tab = BidirectionalTab()
        self.send_tab = SendTab()
        self.receive_tab = ReceiveTab()
        
        self.tab_widget.addTab(self.bidirectional_tab, "双向同步")
        self.tab_widget.addTab(self.send_tab, "发送文件")
        self.tab_widget.addTab(self.receive_tab, "接收文件")
        
        main_layout.addWidget(self.tab_widget)


class BidirectionalTab(QtWidgets.QWidget):
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
        
        # 文件夹路径输入框 - 用于选择要同步的文件夹
        self.folder_edit = QtWidgets.QLineEdit(str(Path.cwd()))
        self.folder_edit.setPlaceholderText("请选择要同步的文件夹路径")
        
        # 浏览按钮 - 打开文件夹选择对话框
        btn_browse = QtWidgets.QPushButton('浏览文件夹')
        btn_browse.clicked.connect(self.on_browse)
        
        folder_layout.addWidget(QtWidgets.QLabel('同步文件夹:'))
        folder_layout.addWidget(self.folder_edit, 1)  # 设置拉伸因子为1
        folder_layout.addWidget(btn_browse)
        layout.addWidget(folder_group)
        
        # === 模式选择区域 ===
        mode_group = QtWidgets.QGroupBox("同步模式选择")
        mode_layout = QtWidgets.QVBoxLayout(mode_group)
        
        # 模式选择按钮组
        self.mode_group = QtWidgets.QButtonGroup(self)
        
        # 监听模式单选按钮 - 作为服务器等待其他设备连接
        self.rb_listen = QtWidgets.QRadioButton('监听模式 (作为服务器)')
        self.rb_listen.setChecked(True)
        self.rb_listen.setToolTip("在此设备上启动服务，等待其他设备连接进行双向同步")
        
        # 连接模式单选按钮 - 连接到其他设备的监听服务
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
        
        # 主机地址输入框 - 仅在连接模式下需要填写
        self.host_edit = QtWidgets.QLineEdit('192.168.1.100')
        self.host_edit.setPlaceholderText("请输入目标设备的IP地址")
        self.host_edit.setToolTip("要连接的设备IP地址，如: 192.168.1.100")
        
        # 端口号输入框 - 同步服务监听的端口号
        self.port_edit = QtWidgets.QLineEdit('9000')
        self.port_edit.setToolTip("同步服务使用的端口号，默认9000")
        
        form_layout.addRow('目标主机地址:', self.host_edit)
        form_layout.addRow('端口号:', self.port_edit)
        layout.addWidget(network_group)
        
        # === 控制按钮区域 ===
        control_group = QtWidgets.QGroupBox("操作控制")
        control_layout = QtWidgets.QHBoxLayout(control_group)
        
        # 开始按钮 - 启动同步过程
        self.btn_start = QtWidgets.QPushButton('开始同步')
        self.btn_start.clicked.connect(self.on_start)
        self.btn_start.setToolTip("开始双向文件同步过程")
        
        # 停止按钮 - 停止同步过程
        self.btn_stop = QtWidgets.QPushButton('停止')
        self.btn_stop.clicked.connect(self.on_stop)
        self.btn_stop.setEnabled(False)
        self.btn_stop.setToolTip("停止当前的同步过程")
        
        control_layout.addWidget(self.btn_start)
        control_layout.addWidget(self.btn_stop)
        control_layout.addStretch(1)  # 添加弹性空间
        layout.addWidget(control_group)
        
        # === 日志显示区域 ===
        log_group = QtWidgets.QGroupBox("同步日志")
        log_layout = QtWidgets.QVBoxLayout(log_group)
        
        # 日志显示文本框 - 显示同步过程中的状态信息
        self.log = QtWidgets.QPlainTextEdit()
        self.log.setReadOnly(True)
        self.log.setPlaceholderText("同步日志将显示在这里...")
        
        # 清空日志按钮
        btn_clear = QtWidgets.QPushButton('清空日志')
        btn_clear.clicked.connect(self.on_clear_log)
        
        log_layout.addWidget(self.log, 1)
        log_layout.addWidget(btn_clear)
        layout.addWidget(log_group, 1)  # 设置日志区域为可拉伸
        
        # 添加弹性空间
        layout.addStretch(1)
    
    def on_browse(self):
        """浏览文件夹按钮点击事件"""
        current_dir = self.folder_edit.text() or str(Path.cwd())
        selected_dir = QtWidgets.QFileDialog.getExistingDirectory(
            self, '选择同步文件夹', current_dir)
        if selected_dir:
            self.folder_edit.setText(selected_dir)
    
    def on_clear_log(self):
        """清空日志按钮点击事件"""
        self.log.clear()
    
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
        self.log.appendPlainText(text)
        # 自动滚动到底部
        scrollbar = self.log.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())
    
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


class SendTab(QtWidgets.QWidget):
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
        self.log.appendPlainText(text)
        scrollbar = self.log.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())
    
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
                # 正确的调用方式：发送方需要主机地址、端口号、文件夹和日志回调函数
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


class ReceiveTab(QtWidgets.QWidget):
    """接收文件模式标签页 - 单向接收来自发送方的文件"""
    
    def __init__(self):
        super().__init__()
        self.sync_thread = None
        self.sync_running = False
        self._build_ui()
    
    def _build_ui(self):
        """构建接收文件界面"""
        layout = QtWidgets.QVBoxLayout(self)
        
        # === 接收文件夹设置 ===
        folder_group = QtWidgets.QGroupBox("接收文件夹设置")
        folder_layout = QtWidgets.QHBoxLayout(folder_group)
        
        self.folder_edit = QtWidgets.QLineEdit(str(Path.cwd()))
        self.folder_edit.setPlaceholderText("选择文件接收保存的文件夹")
        
        btn_browse = QtWidgets.QPushButton('浏览文件夹')
        btn_browse.clicked.connect(self.on_browse)
        
        folder_layout.addWidget(QtWidgets.QLabel('接收文件夹:'))
        folder_layout.addWidget(self.folder_edit, 1)
        folder_layout.addWidget(btn_browse)
        layout.addWidget(folder_group)
        
        # === 网络设置 ===
        network_group = QtWidgets.QGroupBox("网络设置")
        form_layout = QtWidgets.QFormLayout(network_group)
        
        # 获取本机IP地址
        local_ip = self.get_local_ip()
        self.ip_label = QtWidgets.QLabel(f'本机IP地址: {local_ip}')
        self.ip_label.setStyleSheet('color: blue; font-weight: bold;')
        
        self.port_edit = QtWidgets.QLineEdit('9000')
        self.port_edit.setToolTip("接收方监听的端口号")
        
        form_layout.addRow('', self.ip_label)
        form_layout.addRow('监听端口:', self.port_edit)
        layout.addWidget(network_group)
        
        # === 控制按钮 ===
        control_group = QtWidgets.QGroupBox("操作控制")
        control_layout = QtWidgets.QHBoxLayout(control_group)
        
        self.btn_start = QtWidgets.QPushButton('开始接收')
        self.btn_start.clicked.connect(self.on_start)
        self.btn_start.setToolTip("启动监听服务，等待发送方连接")
        
        self.btn_stop = QtWidgets.QPushButton('停止')
        self.btn_stop.clicked.connect(self.on_stop)
        self.btn_stop.setEnabled(False)
        
        control_layout.addWidget(self.btn_start)
        control_layout.addWidget(self.btn_stop)
        control_layout.addStretch(1)
        layout.addWidget(control_group)
        
        # === 日志显示 ===
        log_group = QtWidgets.QGroupBox("接收日志")
        log_layout = QtWidgets.QVBoxLayout(log_group)
        
        self.log = QtWidgets.QPlainTextEdit()
        self.log.setReadOnly(True)
        
        btn_clear = QtWidgets.QPushButton('清空日志')
        btn_clear.clicked.connect(self.on_clear_log)
        
        log_layout.addWidget(self.log, 1)
        log_layout.addWidget(btn_clear)
        layout.addWidget(log_group, 1)
        
        layout.addStretch(1)
    
    def get_local_ip(self):
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
    
    def on_browse(self):
        current_dir = self.folder_edit.text() or str(Path.cwd())
        selected_dir = QtWidgets.QFileDialog.getExistingDirectory(
            self, '选择接收文件夹', current_dir)
        if selected_dir:
            self.folder_edit.setText(selected_dir)
    
    def on_clear_log(self):
        self.log.clear()
    
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
        self.log.appendPlainText(text)
        scrollbar = self.log.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())
    
    def on_start(self):
        if self.sync_running:
            return
        
        folder = self.folder_edit.text().strip()
        if not folder:
            QtWidgets.QMessageBox.warning(self, '错误', '请选择接收文件夹')
            return
        if not os.path.exists(folder):
            QtWidgets.QMessageBox.warning(self, '错误', '选择的文件夹不存在')
            return
        
        port = self.port_edit.text().strip()
        if not port.isdigit():
            QtWidgets.QMessageBox.warning(self, '错误', '端口号必须是数字')
            return
        port = int(port)
        
        self.append_log('启动接收模式...')
        self.append_log(f'正在监听端口 {port}，等待发送方连接...')
        self.append_log(f'请告知发送方使用本机IP地址: {self.get_local_ip()}')
        self.sync_running = True
        self.btn_start.setEnabled(False)
        self.btn_stop.setEnabled(True)
        
        def run_sync():
            try:
                # 正确的调用方式：接收方需要端口号、文件夹、日志回调函数和绑定地址
                sync.run_receive(port, folder, self.append_log, '0.0.0.0')
            except Exception as e:
                self.append_log(f'接收错误: {e}')
            finally:
                self.sync_running = False
                self.append_log('接收完成')
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
            self.append_log('正在停止接收...')
            self.sync_running = False
            self.btn_start.setEnabled(True)
            self.btn_stop.setEnabled(False)


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