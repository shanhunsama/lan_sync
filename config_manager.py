import json
import os
from pathlib import Path

class ConfigManager:
    """配置管理器类"""
    
    def __init__(self, config_file='lan_sync_config.json'):
        self.config_file = config_file
        self.default_config = {
            "bidirectional": {
                "folder": str(Path.cwd()),
                "port": "9000",
                "mode": "listen",
                "host": "192.168.1.100"
            },
            "send": {
                "folder": str(Path.cwd()),
                "host": "192.168.1.100",
                "port": "9000"
            },
            "receive": {
                "folder": str(Path.cwd()),
                "port": "9000"
            },
            "window": {
                "width": 800,
                "height": 600
            },
            "performance": {
                "chunk_size": 262144,  # 256KB
                "socket_buffer_size": 1048576,  # 1MB
                "disable_nagle": True
            }
        }
        self.config = self._load_config()
    
    def _load_config(self):
        """加载配置文件"""
        if os.path.exists(self.config_file):
            try:
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                    # 合并默认配置，确保新字段存在
                    return self._merge_configs(self.default_config, config)
            except Exception as e:
                print(f"加载配置文件失败: {e}")
                return self.default_config.copy()
        else:
            return self.default_config.copy()
    
    def _merge_configs(self, default, current):
        """递归合并配置"""
        merged = default.copy()
        for key, value in current.items():
            if key in merged:
                if isinstance(merged[key], dict) and isinstance(value, dict):
                    merged[key] = self._merge_configs(merged[key], value)
                else:
                    merged[key] = value
        return merged
    
    def save_config(self):
        """保存配置文件"""
        try:
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(self.config, f, indent=4, ensure_ascii=False)
            return True
        except Exception as e:
            print(f"保存配置文件失败: {e}")
            return False
    
    # 双向同步配置方法
    def get_bidirectional_config(self):
        return self.config.get('bidirectional', {})
    
    def set_bidirectional_config(self, config):
        self.config['bidirectional'] = config
    
    # 发送配置方法
    def get_send_config(self):
        return self.config.get('send', {})
    
    def set_send_config(self, config):
        self.config['send'] = config
    
    # 接收配置方法
    def get_receive_config(self):
        return self.config.get('receive', {})
    
    def set_receive_config(self, config):
        self.config['receive'] = config
    
    # 窗口配置方法
    def get_window_config(self):
        return self.config.get('window', {})
    
    def set_window_config(self, config):
        self.config['window'] = config
    
    # 性能配置方法
    def get_performance_config(self):
        return self.config.get('performance', {})
    
    def set_performance_config(self, config):
        self.config['performance'] = config