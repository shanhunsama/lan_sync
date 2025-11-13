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
        
        # 创建标签页控件
        self.tab_widget = QtWidgets.QTabWidget()
        
        # 添加各个模式标签页
        self.bidirectional_tab = BidirectionalTab()
        self.send_tab = SendTab()
        self.receive_tab = ReceiveTab()
        self.performance_tab = PerformanceTab()
        
        self.tab_widget.addTab(self.bidirectional_tab, "双向同步")
        self.tab_widget.addTab(self.send_tab, "发送文件")
        self.tab_widget.addTab(self.receive_tab, "接收文件")
        self.tab_widget.addTab(self.performance_tab, "性能配置")
        
        main_layout.addWidget(self.tab_widget)