"""主窗口模块"""

import sys
from pathlib import Path
from PyQt5 import QtWidgets, QtGui

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from .bidirectional_tab import BidirectionalTab
from .send_tab import SendTab
from .receive_tab import ReceiveTab
from .performance_tab import PerformanceTab


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
        
        # 创建标签页
        self.tabs = QtWidgets.QTabWidget()
        
        # 双向同步标签页
        self.bidirectional_tab = BidirectionalTab()
        self.tabs.addTab(self.bidirectional_tab, "双向同步")
        
        # 发送标签页
        self.send_tab = SendTab()
        self.tabs.addTab(self.send_tab, "发送文件")
        
        # 接收标签页
        self.receive_tab = ReceiveTab()
        self.tabs.addTab(self.receive_tab, "接收文件")
        
        # 性能配置标签页
        self.performance_tab = PerformanceTab()
        self.tabs.addTab(self.performance_tab, "性能配置")
        
        main_layout.addWidget(self.tabs)
        
        # 性能状态显示
        from .performance_status import PerformanceStatusWidget
        self.performance_status = PerformanceStatusWidget()
        main_layout.addWidget(self.performance_status)
        
        # 连接配置变化信号
        self.performance_tab.btn_apply.clicked.connect(self.update_performance_status)
        self.performance_tab.btn_save.clicked.connect(self.update_performance_status)
    
    def update_performance_status(self):
        """更新性能状态显示"""
        performance_config = self.performance_tab.get_performance_config()
        
        status_dict = {
            'memory_mapping': performance_config.get('use_memory_mapping', False),
            'stream_protocol': performance_config.get('use_stream_protocol', False),
            'dynamic_chunk': performance_config.get('dynamic_chunk_size', False),
            'adaptive_threading': performance_config.get('adaptive_threading', False),
            'compression': performance_config.get('enable_compression', False)
        }
        
        self.performance_status.update_status(status_dict)