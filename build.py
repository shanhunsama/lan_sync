#!/usr/bin/env python
"""
打包脚本 - 将LAN同步工具打包为可执行文件
"""

import os
import sys
import subprocess
from pathlib import Path

def install_pyinstaller():
    """安装PyInstaller"""
    print("正在安装PyInstaller...")
    subprocess.check_call([sys.executable, "-m", "pip", "install", "pyinstaller"])

def build_executables():
    """构建可执行文件"""
    print("开始打包程序...")
    
    # 打包命令行版本 (sync.py)
    print("打包命令行版本...")
    subprocess.check_call([
        sys.executable, "-m", "PyInstaller",
        "--onefile",  # 打包为单个文件
        "--console",  # 控制台程序
        "--name=lan-sync",  # 输出文件名
        "--add-data=README.md;.",  # 包含README文件
        "sync.py"
    ])
    
    # 打包GUI版本 (gui.py)
    print("打包GUI版本...")
    subprocess.check_call([
        sys.executable, "-m", "PyInstaller",
        "--onefile",  # 打包为单个文件
        "--windowed",  # 窗口程序（不显示控制台）
        "--name=lan-sync-gui",  # 输出文件名
        "--add-data=README.md;.",  # 包含README文件
        "gui.py"
    ])
    
    print("打包完成！")

def create_spec_files():
    """创建PyInstaller spec文件，用于更精细的控制"""
    
    # sync.py的spec文件
    sync_spec = """
# -*- mode: python ; coding: utf-8 -*-

block_cipher = None

a = Analysis(
    ['sync.py'],
    pathex=[],
    binaries=[],
    datas=[('README.md', '.')],
    hiddenimports=[],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='lan-sync',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
"""
    
    # gui.py的spec文件
    gui_spec = """
# -*- mode: python ; coding: utf-8 -*-

block_cipher = None

a = Analysis(
    ['gui.py'],
    pathex=[],
    binaries=[],
    datas=[('README.md', '.')],
    hiddenimports=['PyQt5.QtCore', 'PyQt5.QtWidgets', 'PyQt5.QtGui'],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='lan-sync-gui',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
"""
    
    # 写入spec文件
    with open('lan-sync.spec', 'w', encoding='utf-8') as f:
        f.write(sync_spec)
    
    with open('lan-sync-gui.spec', 'w', encoding='utf-8') as f:
        f.write(gui_spec)
    
    print("Spec文件创建完成")

def build_with_spec():
    """使用spec文件构建"""
    print("使用spec文件构建可执行文件...")
    
    # 构建命令行版本
    subprocess.check_call([sys.executable, "-m", "PyInstaller", "lan-sync.spec"])
    
    # 构建GUI版本
    subprocess.check_call([sys.executable, "-m", "PyInstaller", "lan-sync-gui.spec"])
    
    print("构建完成！")

def main():
    """主函数"""
    print("LAN同步工具打包程序")
    print("=" * 50)
    
    # 检查是否安装了PyInstaller
    try:
        import PyInstaller
        print("PyInstaller已安装")
    except ImportError:
        print("PyInstaller未安装，正在安装...")
        install_pyinstaller()
    
    # 创建spec文件
    create_spec_files()
    
    # 使用spec文件构建
    build_with_spec()
    
    print("\n打包完成！")
    print("生成的文件在 'dist' 目录下：")
    print("- lan-sync.exe (命令行版本)")
    print("- lan-sync-gui.exe (GUI版本)")
    print("\n使用方法：")
    print("1. 将可执行文件复制到目标电脑")
    print("2. 直接运行即可，无需安装Python")

if __name__ == "__main__":
    main()