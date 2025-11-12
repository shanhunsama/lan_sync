#!/usr/bin/env python
"""Simple Qt front-end for the LAN sync tool

Features:
- Select folder to sync
- Choose mode: listen, connect, send, or receive
- Set host/port
- Import and use sync module directly instead of subprocess
- Show sync progress in a log window

Usage:
    python gui.py

This file uses PyQt5 (listed in requirements.txt).
"""

import sys
import os
import threading
from pathlib import Path
from PyQt5 import QtWidgets, QtCore

# 更稳健的导入方式
try:
    import sync
except ImportError:
    # 打包环境下的导入
    import sys
    from pathlib import Path
    current_dir = Path(__file__).parent
    if str(current_dir) not in sys.path:
        sys.path.insert(0, str(current_dir))
    import sync


class SyncGui(QtWidgets.QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle('LAN Sync - GUI')
        self.resize(700, 480)
        self.sync_thread = None
        self.sync_running = False

        self._build_ui()

    def _build_ui(self):
        layout = QtWidgets.QVBoxLayout(self)

        # folder selection
        h = QtWidgets.QHBoxLayout()
        self.folder_edit = QtWidgets.QLineEdit(str(Path.cwd()))
        btn_browse = QtWidgets.QPushButton('Browse')
        btn_browse.clicked.connect(self.on_browse)
        h.addWidget(QtWidgets.QLabel('Folder:'))
        h.addWidget(self.folder_edit)
        h.addWidget(btn_browse)
        layout.addLayout(h)

        # mode selection and host/port
        form = QtWidgets.QFormLayout()
        self.mode_group = QtWidgets.QButtonGroup(self)
        # keep explicit references to the radio buttons so mode detection is robust
        self.rb_listen = QtWidgets.QRadioButton('Listen (双向)')
        self.rb_connect = QtWidgets.QRadioButton('Connect (双向)')
        self.rb_send = QtWidgets.QRadioButton('Send (单向发送)')
        self.rb_receive = QtWidgets.QRadioButton('Receive (单向接收)')
        self.rb_listen.setChecked(True)
        self.mode_group.addButton(self.rb_listen)
        self.mode_group.addButton(self.rb_connect)
        self.mode_group.addButton(self.rb_send)
        self.mode_group.addButton(self.rb_receive)
        
        # mode selection layout
        h2 = QtWidgets.QHBoxLayout()
        h2.addWidget(self.rb_listen)
        h2.addWidget(self.rb_connect)
        h2.addWidget(self.rb_send)
        h2.addWidget(self.rb_receive)
        form.addRow(QtWidgets.QLabel('Mode:'), h2)

        self.host_edit = QtWidgets.QLineEdit('')
        self.port_edit = QtWidgets.QLineEdit('9000')
        form.addRow('Host (for connect/receive):', self.host_edit)
        form.addRow('Port:', self.port_edit)
        layout.addLayout(form)

        # control buttons
        h3 = QtWidgets.QHBoxLayout()
        self.btn_start = QtWidgets.QPushButton('Start')
        self.btn_stop = QtWidgets.QPushButton('Stop')
        self.btn_stop.setEnabled(False)
        self.btn_start.clicked.connect(self.on_start)
        self.btn_stop.clicked.connect(self.on_stop)
        h3.addWidget(self.btn_start)
        h3.addWidget(self.btn_stop)
        layout.addLayout(h3)

        # log output
        self.log = QtWidgets.QPlainTextEdit()
        self.log.setReadOnly(True)
        layout.addWidget(QtWidgets.QLabel('Log:'))
        layout.addWidget(self.log, 1)

    def append_log(self, text):
        # 使用信号槽机制确保线程安全
        if isinstance(text, tuple) and len(text) > 1:
            format_str = text[0]
            args = text[1:]
            text = format_str % args
        
        # 定义信号
        QtCore.QMetaObject.invokeMethod(
            self, 
            "_safe_append_log", 
            QtCore.Qt.QueuedConnection,
            QtCore.Q_ARG(str, str(text))
        )
    
    @QtCore.pyqtSlot(str)
    def _safe_append_log(self, text):
        """在主线程中安全地添加日志"""
        self.log.appendPlainText(text)
        self.log.verticalScrollBar().setValue(self.log.verticalScrollBar().maximum())

    def on_browse(self):
        d = QtWidgets.QFileDialog.getExistingDirectory(self, 'Select folder', self.folder_edit.text())
        if d:
            self.folder_edit.setText(d)

    def on_start(self):
        if self.sync_running:
            return
            
        folder = self.folder_edit.text().strip()
        if not folder:
            QtWidgets.QMessageBox.warning(self, 'Error', 'Please choose a folder to sync')
            return
        
        if not os.path.exists(folder):
            QtWidgets.QMessageBox.warning(self, 'Error', 'Selected folder does not exist')
            return
        
        # determine mode
        if self.rb_listen.isChecked():
            mode = 'listen'
        elif self.rb_connect.isChecked():
            mode = 'connect'
        elif self.rb_send.isChecked():
            mode = 'send'
        elif self.rb_receive.isChecked():
            mode = 'receive'
        else:
            QtWidgets.QMessageBox.warning(self, 'Error', 'Please select a mode')
            return
            
        port = self.port_edit.text().strip()
        if not port.isdigit():
            QtWidgets.QMessageBox.warning(self, 'Error', 'Port must be a number')
            return
        port = int(port)
        
        if mode in ['connect', 'receive']:
            host = self.host_edit.text().strip()
            if not host:
                QtWidgets.QMessageBox.warning(self, 'Error', 'Please enter host to connect to')
                return

        self.append_log(f'Starting {mode} mode...')
        self.sync_running = True
        self.btn_start.setEnabled(False)
        self.btn_stop.setEnabled(True)

        # 在单独的线程中运行同步逻辑
        def run_sync():
            try:
                if mode == 'listen':
                    sync.run_listen(port, folder, self.append_log)
                elif mode == 'connect':
                    sync.run_connect(host, port, folder, self.append_log)
                elif mode == 'send':
                    sync.run_send(port, folder, self.append_log)
                elif mode == 'receive':
                    sync.run_receive(host, port, folder, self.append_log)
            except Exception as e:
                self.append_log(f'Sync error: {e}')
            finally:
                self.sync_running = False
                self.append_log('Sync finished')
                # 使用信号槽机制更新UI
                QtCore.QMetaObject.invokeMethod(self, "on_sync_finished", QtCore.Qt.QueuedConnection)

        self.sync_thread = threading.Thread(target=run_sync, daemon=True)
        self.sync_thread.start()

    @QtCore.pyqtSlot()
    def on_sync_finished(self):
        self.btn_start.setEnabled(True)
        self.btn_stop.setEnabled(False)

    def on_stop(self):
        if self.sync_running:
            self.append_log('Stopping sync...')
            self.sync_running = False
            # 这里无法直接停止同步线程，但可以设置标志让线程自然结束
            self.btn_start.setEnabled(True)
            self.btn_stop.setEnabled(False)

def main():
    app = QtWidgets.QApplication(sys.argv)
    w = SyncGui()
    w.show()
    sys.exit(app.exec_())

if __name__ == '__main__':
    main()