# LAN同步工具打包说明

## 打包方法

### 方法一：使用批处理脚本（推荐）
1. 双击运行 `build.bat`
2. 等待打包完成
3. 在 `dist` 目录下找到生成的可执行文件

### 方法二：手动打包
1. 安装PyInstaller：
   ```bash
   pip install pyinstaller
   ```
2. 运行打包脚本：
   ```bash
   python build.py
   ```

## 生成的文件

打包完成后，在 `dist` 目录下会生成：

- `lan-sync.exe` - 命令行版本
- `lan-sync-gui.exe` - 图形界面版本

## 使用方法

### 在目标电脑上使用

1. 将可执行文件复制到目标电脑
2. 无需安装Python或其他依赖
3. 直接双击运行即可

### 命令行版本使用

```bash
# 双向同步模式
lan-sync.exe --listen --port 9000
lan-sync.exe --connect 192.168.1.100 --port 9000

# 单向传输模式
lan-sync.exe --send --port 9000
lan-sync.exe --receive 192.168.1.100 --port 9000
```

### GUI版本使用
- 双击 `lan-sync-gui.exe` 启动图形界面
- 选择文件夹和模式后点击"Start"开始同步

## 系统要求

- Windows 7/8/10/11 (64位)
- 无需安装Python运行环境
- 需要网络连接（局域网）

## 文件大小说明

打包后的可执行文件会比较大（约50-100MB），这是因为包含了Python解释器和所有依赖库。这是正常的，文件会在运行时解压到临时目录。

## 注意事项

1. 首次运行时杀毒软件可能会报警，请选择"允许运行"
2. 确保防火墙允许程序访问网络
3. 如果遇到问题，可以尝试以管理员身份运行