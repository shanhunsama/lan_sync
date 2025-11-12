#!/usr/bin/env python
"""Simple Qt front-end for the LAN sync tool

Features:
- Select folder to sync
- Choose mode: listen or connect
- Set host/port
- Start/Stop the underlying `sync.py` as a subprocess (working dir = chosen folder)
- Show process stdout/stderr in a log window

Usage:
    python gui.py

This file uses PyQt5 (listed in requirements.txt).
"""

import sys
import os
from pathlib import Path
from PyQt5 import QtWidgets, QtCore


class SyncGui(QtWidgets.QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle('LAN Sync - GUI')
        self.resize(700, 480)
        self.proc = QtCore.QProcess(self)
        self.proc.readyReadStandardOutput.connect(self.on_stdout)
        self.proc.readyReadStandardError.connect(self.on_stderr)
        self.proc.finished.connect(self.on_finished)

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
        self.rb_listen = QtWidgets.QRadioButton('Listen')
        self.rb_connect = QtWidgets.QRadioButton('Connect')
        self.rb_listen.setChecked(True)
        self.mode_group.addButton(self.rb_listen)
        self.mode_group.addButton(self.rb_connect)
        h2 = QtWidgets.QHBoxLayout()
        h2.addWidget(self.rb_listen)
        h2.addWidget(self.rb_connect)
        form.addRow(QtWidgets.QLabel('Mode:'), h2)

        self.host_edit = QtWidgets.QLineEdit('')
        self.port_edit = QtWidgets.QLineEdit('9000')
        form.addRow('Host (for connect):', self.host_edit)
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
        self.log.appendPlainText(text)

    def on_browse(self):
        d = QtWidgets.QFileDialog.getExistingDirectory(self, 'Select folder', self.folder_edit.text())
        if d:
            self.folder_edit.setText(d)

    def on_start(self):
        folder = self.folder_edit.text().strip()
        if not folder:
            QtWidgets.QMessageBox.warning(self, 'Error', 'Please choose a folder to sync')
            return
        # use explicit button state rather than relying on ordering in mode_group.buttons()
        mode = 'listen' if self.rb_listen.isChecked() else 'connect'
        port = self.port_edit.text().strip()
        if not port.isdigit():
            QtWidgets.QMessageBox.warning(self, 'Error', 'Port must be a number')
            return
        # build command
        script_dir = Path(__file__).parent
        sync_py = str(script_dir / 'sync.py')
        cmd = [sys.executable, sync_py]
        if mode == 'listen':
            cmd += ['--listen', '--port', port]
        else:
            host = self.host_edit.text().strip()
            if not host:
                QtWidgets.QMessageBox.warning(self, 'Error', 'Please enter host to connect to')
                return
            cmd += ['--connect', host, '--port', port]

        self.append_log('Starting: ' + ' '.join(cmd))
        # set working directory to selected folder
        self.proc.setWorkingDirectory(folder)
        # start process
        self.proc.start(cmd[0], cmd[1:])
        started = self.proc.waitForStarted(3000)
        if not started:
            self.append_log('Failed to start process')
            return
        self.btn_start.setEnabled(False)
        self.btn_stop.setEnabled(True)

    def on_stop(self):
        if self.proc.state() != QtCore.QProcess.NotRunning:
            self.append_log('Stopping process...')
            self.proc.terminate()
            if not self.proc.waitForFinished(3000):
                self.proc.kill()
        self.btn_start.setEnabled(True)
        self.btn_stop.setEnabled(False)

    def on_stdout(self):
        data = self.proc.readAllStandardOutput().data().decode('utf-8', errors='replace')
        for line in data.splitlines():
            self.append_log('[OUT] ' + line)

    def on_stderr(self):
        data = self.proc.readAllStandardError().data().decode('utf-8', errors='replace')
        for line in data.splitlines():
            self.append_log('[ERR] ' + line)

    def on_finished(self, code, status):
        self.append_log(f'Process finished (code={code}, status={status})')
        self.btn_start.setEnabled(True)
        self.btn_stop.setEnabled(False)


def main():
    app = QtWidgets.QApplication(sys.argv)
    w = SyncGui()
    w.show()
    sys.exit(app.exec_())


if __name__ == '__main__':
    main()
