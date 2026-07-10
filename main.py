"""
历史报刊主题分析工具
主入口文件
"""
import sys
import os

# 确保项目根目录在 sys.path 中
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

try:
    from PySide6.QtWidgets import QApplication
    from PySide6.QtCore import Qt
    from PySide6.QtGui import QFont
except ModuleNotFoundError as e:
    if getattr(e, "name", "") == "PySide6":
        print(
            "错误：当前启动这个程序的 Python 环境中没有安装 PySide6。\n"
            "这通常不是没装，而是‘安装 PySide6 的 Python’和‘运行 main.py 的 Python’不是同一个。\n\n"
            "请在当前目录尝试：\n"
            "  python -m pip show PySide6\n"
            "  python -m pip install -r requirements.txt\n"
            "  python main.py\n\n"
            "如果你使用的是 Windows，也可以尝试：\n"
            "  py -m pip show PySide6\n"
            "  py -m pip install -r requirements.txt\n"
            "  py main.py\n"
        )
        raise SystemExit(1)
    raise

from gui.main_window import MainWindow


def main():
    app = QApplication(sys.argv)
    app.setApplicationName("历史报刊主题分析工具")
    app.setApplicationVersion("1.0.0")

    # 高 DPI 支持
    app.setHighDpiScaleFactorRoundingPolicy(
        Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
    )

    # 默认字体（优先使用系统中文字体）
    for font_name in ["Microsoft YaHei", "PingFang SC", "Noto Sans CJK SC", "SimHei", "Arial"]:
        font = QFont(font_name, 10)
        if font.exactMatch() or font_name == "Arial":
            app.setFont(font)
            break

    window = MainWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
