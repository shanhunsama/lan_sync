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
            "较大的缓冲区可以提高网络传输效率。\n"
            "高级优化功能可以进一步提升传输性能。"
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
        
        # === 高级优化设置 ===
        optimization_group = QtWidgets.QGroupBox("高级优化设置")
        optimization_layout = QtWidgets.QFormLayout(optimization_group)
        
        # 内存映射优化
        self.memory_mapping_checkbox = QtWidgets.QCheckBox("启用内存映射传输 (推荐)")
        self.memory_mapping_checkbox.setToolTip("使用内存映射技术减少系统调用，提高大文件传输速度")
        
        # 流式协议优化
        self.stream_protocol_checkbox = QtWidgets.QCheckBox("启用流式协议 (推荐)")
        self.stream_protocol_checkbox.setToolTip("使用流式协议消除长度前缀开销，提高传输效率")
        
        # 动态块大小调整
        self.dynamic_chunk_checkbox = QtWidgets.QCheckBox("启用动态块大小调整")
        self.dynamic_chunk_checkbox.setToolTip("根据文件大小自动调整块大小，优化不同大小文件的传输")
        
        # 自适应线程数
        self.adaptive_threading_checkbox = QtWidgets.QCheckBox("启用自适应线程数")
        self.adaptive_threading_checkbox.setToolTip("根据文件大小自动调整并发线程数")
        
        # 压缩传输
        self.compression_checkbox = QtWidgets.QCheckBox("启用压缩传输")
        self.compression_checkbox.setToolTip("对可压缩文件进行实时压缩传输")
        
        # 压缩阈值
        self.compression_threshold_combo = QtWidgets.QComboBox()
        self.compression_threshold_combo.addItem("100KB", 102400)
        self.compression_threshold_combo.addItem("500KB", 512000)
        self.compression_threshold_combo.addItem("1MB (推荐)", 1048576)
        self.compression_threshold_combo.addItem("5MB", 5242880)
        self.compression_threshold_combo.addItem("10MB", 10485760)
        self.compression_threshold_combo.setToolTip("文件大小超过此阈值时启用压缩")
        
        optimization_layout.addRow('', self.memory_mapping_checkbox)
        optimization_layout.addRow('', self.stream_protocol_checkbox)
        optimization_layout.addRow('', self.dynamic_chunk_checkbox)
        optimization_layout.addRow('', self.adaptive_threading_checkbox)
        optimization_layout.addRow('', self.compression_checkbox)
        optimization_layout.addRow('压缩阈值:', self.compression_threshold_combo)
        layout.addWidget(optimization_group)
        
        # === 性能测试区域 ===
        test_group = QtWidgets.QGroupBox("性能测试")
        test_layout = QtWidgets.QVBoxLayout(test_group)
        
        # 测试按钮
        self.btn_test = QtWidgets.QPushButton('运行性能测试')
        self.btn_test.clicked.connect(self.on_run_test)
        self.btn_test.setStyleSheet("background-color: #FF9800; color: white; font-weight: bold;")
        
        # 测试结果显示
        self.test_result_text = QtWidgets.QTextEdit()
        self.test_result_text.setMaximumHeight(120)
        self.test_result_text.setReadOnly(True)
        self.test_result_text.setPlaceholderText("性能测试结果将显示在这里...")
        
        test_layout.addWidget(self.btn_test)
        test_layout.addWidget(self.test_result_text)
        layout.addWidget(test_group)
        
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
        
        # 设置高级优化选项
        self.memory_mapping_checkbox.setChecked(
            performance_config.get('use_memory_mapping', True)
        )
        self.stream_protocol_checkbox.setChecked(
            performance_config.get('use_stream_protocol', True)
        )
        self.dynamic_chunk_checkbox.setChecked(
            performance_config.get('dynamic_chunk_size', True)
        )
        self.adaptive_threading_checkbox.setChecked(
            performance_config.get('adaptive_threading', True)
        )
        self.compression_checkbox.setChecked(
            performance_config.get('enable_compression', False)
        )
        
        # 设置压缩阈值
        compression_threshold = performance_config.get('compression_threshold', 1048576)
        index = self.compression_threshold_combo.findData(compression_threshold)
        if index >= 0:
            self.compression_threshold_combo.setCurrentIndex(index)
        
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
            'thread_count': self.thread_count_spin.value(),
            'use_memory_mapping': self.memory_mapping_checkbox.isChecked(),
            'use_stream_protocol': self.stream_protocol_checkbox.isChecked(),
            'dynamic_chunk_size': self.dynamic_chunk_checkbox.isChecked(),
            'adaptive_threading': self.adaptive_threading_checkbox.isChecked(),
            'enable_compression': self.compression_checkbox.isChecked(),
            'compression_threshold': self.compression_threshold_combo.currentData(),
            'max_chunk_size': 1048576,  # 1MB
            'min_chunk_size': 65536     # 64KB
        }
        self.config_manager.set_performance_config(performance_config)
    
    def on_run_test(self):
        """运行性能测试"""
        try:
            from core.performance_tester import PerformanceTester
            tester = PerformanceTester()
            
            # 创建测试文件
            test_file = "test_performance.bin"
            test_size = 50 * 1024 * 1024  # 50MB
            
            import os
            if not os.path.exists(test_file):
                self.test_result_text.append("正在创建测试文件...")
                with open(test_file, 'wb') as f:
                    f.write(b'0' * test_size)
            
            self.test_result_text.append("开始性能测试...")
            avg_speed, std_dev = tester.test_transfer_speed(test_file, iterations=3)
            report = tester.generate_report()
            
            self.test_result_text.clear()
            self.test_result_text.append(report)
            self.test_result_text.append(f"\n测试文件: {test_file} ({test_size/(1024*1024):.1f}MB)")
            
        except Exception as e:
            self.test_result_text.append(f"性能测试失败: {str(e)}")
    
    def get_performance_config(self):
        """获取当前性能配置"""
        return self.config_manager.get_performance_config()