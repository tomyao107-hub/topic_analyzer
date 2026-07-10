"""
底部状态栏组件
"""
from PySide6.QtWidgets import (
    QWidget, QHBoxLayout, QLabel, QProgressBar
)
from PySide6.QtCore import Qt


class StatusBar(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("BottomBar")
        self.setFixedHeight(32)
        self._setup_ui()

    def _setup_ui(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 0, 12, 0)
        layout.setSpacing(12)

        self._status_label = QLabel("就绪")
        self._status_label.setObjectName("StatusLabel")
        layout.addWidget(self._status_label)

        layout.addStretch()

        self._progress = QProgressBar()
        self._progress.setFixedWidth(160)
        self._progress.setFixedHeight(4)
        self._progress.setVisible(False)
        self._progress.setTextVisible(False)
        layout.addWidget(self._progress)

        self._progress_label = QLabel("")
        self._progress_label.setStyleSheet("color: #64748B; font-size: 11px;")
        self._progress_label.setVisible(False)
        layout.addWidget(self._progress_label)

    def set_status(self, text: str, level: str = "info"):
        """设置状态文本，level: info / success / warning / error"""
        colors = {
            "info": "#475569",
            "success": "#16A34A",
            "warning": "#D97706",
            "error": "#DC2626",
        }
        color = colors.get(level, "#475569")
        self._status_label.setText(text)
        self._status_label.setStyleSheet(f"color: {color}; font-size: 12px; padding: 0 12px;")

    def show_progress(self, value: int = 0, maximum: int = 100, label: str = ""):
        """显示进度条"""
        self._progress.setMaximum(maximum)
        self._progress.setValue(value)
        self._progress.setVisible(True)
        if label:
            self._progress_label.setText(label)
            self._progress_label.setVisible(True)
        else:
            self._progress_label.setVisible(False)

    def hide_progress(self):
        """隐藏进度条"""
        self._progress.setVisible(False)
        self._progress_label.setVisible(False)

    def set_indeterminate(self, label: str = "处理中..."):
        """设置不确定进度"""
        self._progress.setMaximum(0)
        self._progress.setValue(0)
        self._progress.setVisible(True)
        self._progress_label.setText(label)
        self._progress_label.setVisible(True)
