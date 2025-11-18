"""性能测试模块"""

import time
import threading
import statistics
from pathlib import Path

class PerformanceTester:
    """性能测试器"""
    
    def __init__(self):
        self.results = {}
    
    def test_transfer_speed(self, test_file_path, iterations=5):
        """测试传输速度"""
        if not Path(test_file_path).exists():
            raise FileNotFoundError(f"测试文件不存在: {test_file_path}")
        
        file_size = Path(test_file_path).stat().st_size
        speeds = []
        
        for i in range(iterations):
            start_time = time.time()
            
            # 模拟传输过程（这里需要实际的传输代码）
            # 暂时使用文件复制来模拟
            temp_path = f"{test_file_path}.test_{i}"
            with open(test_file_path, 'rb') as src, open(temp_path, 'wb') as dst:
                while True:
                    chunk = src.read(262144)  # 256KB
                    if not chunk:
                        break
                    dst.write(chunk)
            
            end_time = time.time()
            duration = end_time - start_time
            speed_mbps = (file_size / duration) / (1024 * 1024)  # MB/s
            
            speeds.append(speed_mbps)
            
            # 清理临时文件
            Path(temp_path).unlink(missing_ok=True)
        
        avg_speed = statistics.mean(speeds)
        std_dev = statistics.stdev(speeds) if len(speeds) > 1 else 0
        
        self.results['transfer_speed'] = {
            'average_mbps': avg_speed,
            'std_dev': std_dev,
            'iterations': iterations,
            'file_size_mb': file_size / (1024 * 1024)
        }
        
        return avg_speed, std_dev
    
    def generate_report(self):
        """生成性能报告"""
        report = "# LAN Sync 性能优化报告\n\n"
        
        if 'transfer_speed' in self.results:
            speed_data = self.results['transfer_speed']
            report += f"## 传输速度测试\n"
            report += f"- 平均速度: {speed_data['average_mbps']:.2f} MB/s\n"
            report += f"- 标准差: {speed_data['std_dev']:.2f} MB/s\n"
            report += f"- 测试次数: {speed_data['iterations']}\n"
            report += f"- 文件大小: {speed_data['file_size_mb']:.2f} MB\n\n"
            
            # 性能评估
            if speed_data['average_mbps'] > 100:
                report += "**性能评级: 优秀** 🚀\n"
            elif speed_data['average_mbps'] > 80:
                report += "**性能评级: 良好** 👍\n"
            elif speed_data['average_mbps'] > 60:
                report += "**性能评级: 一般** ⚡\n"
            else:
                report += "**性能评级: 需要优化** 🔧\n"
        
        return report

# 使用示例
if __name__ == "__main__":
    tester = PerformanceTester()
    
    # 测试一个100MB的文件
    test_file = "test_100mb.bin"
    
    # 如果测试文件不存在，创建一个
    if not Path(test_file).exists():
        print("创建测试文件...")
        with open(test_file, 'wb') as f:
            f.write(b'0' * 100 * 1024 * 1024)  # 100MB
    
    avg_speed, std_dev = tester.test_transfer_speed(test_file)
    print(tester.generate_report())