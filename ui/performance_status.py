"""性能优化状态显示组件"""

from PyQt5 import QtWidgets, QtCore

class PerformanceStatusWidget(QtWidgets.QWidget):
    """性能优化状态显示组件"""
    
    def __init__(self):
        super().__init__()
        self._build_ui()
    
    def _build_ui(self):
        """构建界面"""
        layout = QtWidgets.QVBoxLayout(self)
        
        # 状态标题
        title_label = QtWidgets.QLabel("性能优化状态")
        title_label.setStyleSheet("font-weight: bold; font-size: 14px; color: #333;")
        layout.addWidget(title_label)
        
        # 优化状态列表
        self.status_list = QtWidgets.QListWidget()
        self.status_list.setMaximumHeight(150)
        
        # 初始化状态
        self.update_status({
            'memory_mapping': False,
            'stream_protocol': False,
            'dynamic_chunk': False,
            'adaptive_threading': False,
            'compression': False
        })
        
        layout.addWidget(self.status_list)
    
    def update_status(self, status_dict):
        """更新优化状态"""
        self.status_list.clear()
        
        status_items = [
            ("内存映射传输", status_dict.get('memory_mapping', False), 
             "使用内存映射技术减少系统调用"),
            ("流式协议优化", status_dict.get('stream_protocol', False),
             "消除长度前缀开销，提高传输效率"),
            ("动态块大小调整", status_dict.get('dynamic_chunk', False),
             "根据文件大小自动优化块大小"),
            ("自适应线程数", status_dict.get('adaptive_threading', False),
             "根据文件大小自动调整并发线程"),
            ("压缩传输", status_dict.get('compression', False),
             "对可压缩文件进行实时压缩")
        ]
        
        for name, enabled, description in status_items:
            item = QtWidgets.QListWidgetItem()
            
            if enabled:
                item.setText(f"✅ {name}: {description}")
                item.setBackground(QtCore.Qt.green)
            else:
                item.setText(f"❌ {name}: {description}")
                item.setBackground(QtCore.Qt.lightGray)
            
            self.status_list.addItem(item)