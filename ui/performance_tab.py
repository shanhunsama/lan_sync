"""性能配置标签页模块"""

import sys
from pathlib import Path
from PyQt5 import QtWidgets, QtCore

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from config_manager import ConfigManager


class PerformanceTab(QtWidgets.QWidget):
    """性能配置标签页 - 配置传输性能参数"""
    
    def __init__(self):
        super().__init__()
        self.config_manager = ConfigManager()
        self._build_ui()
        self._load_current_settings()
    
    def _build_ui(self):
        """构建性能配置界面"""
        layout = QtWidgets.QVBoxLayout(self)
        
        # === 性能配置说明 ===
        info_group = QtWidgets.QGroupBox("性能配置说明")
        info_layout = QtWidgets.QVBoxLayout(info_group)
        
        info_label = QtWidgets.QLabel(
            "配置传输性能参数以优化文件同步速度和资源使用。\n"
            "较大的块大小可以提高传输速度，但会占用更多内存。\n"
            "较大的缓冲区可以提高网络传输效率。"
        )
        info_label.setWordWrap(True)
        info_label.setStyleSheet("color: #666; font-size: 12px;")
        
        info_layout.addWidget(info_label)
        layout.addWidget(info_group)
        
        # === 传输性能设置 ===
        performance_group = QtWidgets.QGroupBox("传输性能设置")
        form_layout = QtWidgets.QFormLayout(performance_group)
        
        # 块大小设置
        self.chunk_size_combo = QtWidgets.QComboBox()
        self.chunk_size_combo.addItem("64KB (标准)", 65536)
        self.chunk_size_combo.addItem("128KB (推荐)", 131072)
        self.chunk_size_combo.addItem("256KB (高速)", 262144)
        self.chunk_size_combo.addItem("512KB (极速)", 524288)
        self.chunk_size_combo.addItem("1MB (最大)", 1048576)
        self.chunk_size_combo.setToolTip("每次传输的数据块大小，较大的块可以提高传输速度")
        
        # 套接字缓冲区大小
        self.buffer_size_combo = QtWidgets.QComboBox()
        self.buffer_size_combo.addItem("256KB", 262144)
        self.buffer_size_combo.addItem("512KB", 524288)
        self.buffer_size_combo.addItem("1MB (推荐)", 1048576)
        self.buffer_size_combo.addItem("2MB", 2097152)
        self.buffer_size_combo.addItem("4MB (最大)", 4194304)
        self.buffer_size_combo.setToolTip("网络套接字缓冲区大小，较大的缓冲区可以提高网络传输效率")
        
        # Nagle算法开关
        self.nagle_checkbox = QtWidgets.QCheckBox("禁用Nagle算法 (推荐)")
        self.nagle_checkbox.setToolTip("禁用Nagle算法可以减少网络延迟，提高小文件传输速度")
        
        # 并发线程数
        self.thread_count_spin = QtWidgets.QSpinBox()
        self.thread_count_spin.setRange(1, 16)
        self.thread_count_spin.setValue(4)
        self.thread_count_spin.setToolTip("并发传输线程数，较多的线程可以提高多文件传输速度")
        
        form_layout.addRow('数据块大小:', self.chunk_size_combo)
        form_layout.addRow('缓冲区大小:', self.buffer_size_combo)
        form_layout.addRow('', self.nagle_checkbox)
        form_layout.addRow('并发线程数:', self.thread_count_spin)
        layout.addWidget(performance_group)
        
        # === 控制按钮 ===
        button_layout = QtWidgets.QHBoxLayout()
        
        # 保存按钮
        self.btn_save = QtWidgets.QPushButton('保存配置')
        self.btn_save.clicked.connect(self.on_save)
        self.btn_save.setStyleSheet("background-color: #4CAF50; color: white;")
        
        # 重置按钮
        self.btn_reset = QtWidgets.QPushButton('重置为默认')
        self.btn_reset.clicked.connect(self.on_reset)
        self.btn_reset.setStyleSheet("background-color: #f44336; color: white;")
        
        # 应用按钮
        self.btn_apply = QtWidgets.QPushButton('应用配置')
        self.btn_apply.clicked.connect(self.on_apply)
        self.btn_apply.setStyleSheet("background-color: #2196F3; color: white;")
        
        button_layout.addWidget(self.btn_save)
        button_layout.addWidget(self.btn_reset)
        button_layout.addWidget(self.btn_apply)
        button_layout.addStretch(1)
        layout.addLayout(button_layout)
        
        # === 状态显示 ===
        self.status_label = QtWidgets.QLabel("配置已加载")
        self.status_label.setAlignment(QtCore.Qt.AlignCenter)
        self.status_label.setStyleSheet("color: green; font-weight: bold;")
        layout.addWidget(self.status_label)
        
        layout.addStretch(1)
    
    def _load_current_settings(self):
        """加载当前性能配置"""
        performance_config = self.config_manager.get_performance_config()
        
        # 设置块大小
        chunk_size = performance_config.get('chunk_size', 262144)
        index = self.chunk_size_combo.findData(chunk_size)
        if index >= 0:
            self.chunk_size_combo.setCurrentIndex(index)
        
        # 设置缓冲区大小
        buffer_size = performance_config.get('socket_buffer_size', 1048576)
        index = self.buffer_size_combo.findData(buffer_size)
        if index >= 0:
            self.buffer_size_combo.setCurrentIndex(index)
        
        # 设置Nagle算法
        disable_nagle = performance_config.get('disable_nagle', True)
        self.nagle_checkbox.setChecked(disable_nagle)
        
        # 设置线程数
        thread_count = performance_config.get('thread_count', 4)
        self.thread_count_spin.setValue(thread_count)
        
        self.status_label.setText("当前配置已加载")
        self.status_label.setStyleSheet("color: green; font-weight: bold;")
    
    def on_save(self):
        """保存配置到文件"""
        self._save_settings()
        if self.config_manager.save_config():
            self.status_label.setText("配置已保存到文件")
            self.status_label.setStyleSheet("color: green; font-weight: bold;")
        else:
            self.status_label.setText("保存配置失败")
            self.status_label.setStyleSheet("color: red; font-weight: bold;")
    
    def on_reset(self):
        """重置为默认配置"""
        # 重置为默认值
        self.chunk_size_combo.setCurrentIndex(2)  # 256KB
        self.buffer_size_combo.setCurrentIndex(2)  # 1MB
        self.nagle_checkbox.setChecked(True)
        self.thread_count_spin.setValue(4)
        
        self.status_label.setText("已重置为默认配置")
        self.status_label.setStyleSheet("color: blue; font-weight: bold;")
    
    def on_apply(self):
        """应用当前配置（不保存到文件）"""
        self._save_settings()
        self.status_label.setText("配置已应用（内存中）")
        self.status_label.setStyleSheet("color: orange; font-weight: bold;")
    
    def _save_settings(self):
        """保存当前设置到配置管理器"""
        performance_config = {
            'chunk_size': self.chunk_size_combo.currentData(),
            'socket_buffer_size': self.buffer_size_combo.currentData(),
            'disable_nagle': self.nagle_checkbox.isChecked(),
            'thread_count': self.thread_count_spin.value()
        }
        self.config_manager.set_performance_config(performance_config)
    
    def get_performance_config(self):
        """获取当前性能配置"""
        return self.config_manager.get_performance_config()