"""
左侧导航栏组件
"""
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QLabel, QPushButton, QFrame, QSizePolicy
)
from PySide6.QtCore import Signal, Qt
from PySide6.QtGui import QFont

# 导航项配置: (object_name, 图标, 文字, 步骤要求)
NAV_ITEMS = [
    ("welcome",   "🏠", "首页",    None),
    ("import",    "📥", "数据导入", None),
    ("clean",     "🧹", "数据清洗", "imported"),
    ("lda",       "📊", "LDA 分析",  "cleaned"),
    ("stm",       "🔬", "STM 分析",  "cleaned"),
    ("compare",   "⚖️", "对比分析", "lda_done"),
    ("export",    "📤", "导出结果", "imported"),
]


class NavBar(QWidget):
    page_changed = Signal(str)   # 发出页面名称

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("NavBar")
        self._buttons = {}
        self._current = "welcome"
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # 标题区域
        title_widget = QWidget()
        title_widget.setObjectName("NavBar")
        title_layout = QVBoxLayout(title_widget)
        title_layout.setContentsMargins(16, 20, 16, 12)
        title_layout.setSpacing(2)

        title = QLabel("📰 报刊主题分析")
        title.setObjectName("NavTitle")
        title_layout.addWidget(title)

        subtitle = QLabel("数字人文研究工具 v1.0")
        subtitle.setObjectName("NavSubtitle")
        title_layout.addWidget(subtitle)

        layout.addWidget(title_widget)

        # 分隔线
        sep = QFrame()
        sep.setFrameShape(QFrame.HLine)
        sep.setObjectName("NavSeparator")
        sep.setStyleSheet("background-color: #334155; max-height: 1px; margin: 0 16px;")
        layout.addWidget(sep)
        layout.addSpacing(8)

        # 导航按钮
        for name, icon, text, _ in NAV_ITEMS:
            btn = QPushButton(f"  {icon}  {text}")
            btn.setObjectName("NavButton")
            btn.setCheckable(False)
            btn.setCursor(Qt.PointingHandCursor)
            btn.clicked.connect(lambda checked, n=name: self._on_click(n))
            self._buttons[name] = btn
            layout.addWidget(btn)

        layout.addStretch()

        # 版权信息
        copy_label = QLabel("© 2024 数字人文实验室")
        copy_label.setStyleSheet("color: #475569; font-size: 10px; padding: 12px 16px;")
        copy_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(copy_label)

        # 默认选中首页
        self._set_active("welcome")

    def _on_click(self, name: str):
        self._set_active(name)
        self.page_changed.emit(name)

    def _set_active(self, name: str):
        for n, btn in self._buttons.items():
            btn.setProperty("active", "true" if n == name else "false")
            btn.style().unpolish(btn)
            btn.style().polish(btn)
        self._current = name

    def set_active(self, name: str):
        """外部调用切换活动页"""
        self._set_active(name)

    def update_step_states(self, imported: bool, merged: bool,
                           cleaned: bool, lda_done: bool, stm_done: bool):
        """根据流程完成状态更新按钮可用性"""
        states = {
            "imported": imported or merged,
            "merged": merged,
            "cleaned": cleaned,
            "lda_done": lda_done,
            "stm_done": stm_done,
        }
        for name, icon, text, requires in NAV_ITEMS:
            if requires and name in self._buttons:
                enabled = states.get(requires, False)
                self._buttons[name].setEnabled(enabled)
                tip = "" if enabled else f"请先完成上一步骤"
                self._buttons[name].setToolTip(tip)
