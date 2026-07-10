"""
主窗口
QMainWindow + 左侧导航 + 中央堆叠页面 + 顶部工具栏 + 底部状态栏
"""
from PySide6.QtWidgets import (
    QMainWindow, QWidget, QHBoxLayout, QVBoxLayout,
    QLabel, QStackedWidget, QPushButton, QFrame, QSizePolicy
)
from PySide6.QtCore import Qt, Slot
from PySide6.QtGui import QFont

from gui.styles import APP_STYLE
from gui.widgets.nav_bar import NavBar
from gui.widgets.status_bar import StatusBar
from models.app_state import get_state
from utils.logger import log_signals, setup_logger


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        setup_logger()
        self.setWindowTitle("历史报刊主题分析工具")
        self.setMinimumSize(1200, 750)
        self.resize(1400, 860)
        self.setStyleSheet(APP_STYLE)

        self._pages = {}
        self._setup_ui()
        self._connect_signals()

        # 初始显示首页
        self._switch_page("welcome")

    def _setup_ui(self):
        central = QWidget()
        self.setCentralWidget(central)

        main_layout = QVBoxLayout(central)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # 顶部工具栏
        top_bar = self._build_top_bar()
        main_layout.addWidget(top_bar)

        # 主体区（导航 + 内容）
        body = QWidget()
        body_layout = QHBoxLayout(body)
        body_layout.setContentsMargins(0, 0, 0, 0)
        body_layout.setSpacing(0)

        # 左侧导航
        self.nav_bar = NavBar()
        self.nav_bar.page_changed.connect(self._switch_page)
        body_layout.addWidget(self.nav_bar)

        # 右侧页面堆叠
        self.stack = QStackedWidget()
        self.stack.setObjectName("ContentStack")
        body_layout.addWidget(self.stack, 1)

        main_layout.addWidget(body, 1)

        # 底部状态栏
        self.status_bar_widget = StatusBar()
        main_layout.addWidget(self.status_bar_widget)

        # 延迟创建页面（避免循环导入）
        self._create_pages()

    def _build_top_bar(self) -> QWidget:
        bar = QFrame()
        bar.setObjectName("TopBar")
        bar.setFixedHeight(56)

        layout = QHBoxLayout(bar)
        layout.setContentsMargins(20, 0, 20, 0)
        layout.setSpacing(12)

        title = QLabel("📰 历史报刊主题分析工具")
        title.setObjectName("AppTitle")
        layout.addWidget(title)

        sep = QLabel("·")
        sep.setStyleSheet("color: #CBD5E1;")
        layout.addWidget(sep)

        self._project_label = QLabel("未命名项目")
        self._project_label.setObjectName("ProjectLabel")
        layout.addWidget(self._project_label)

        layout.addStretch()

        self._status_chip = QLabel("尚未导入数据")
        self._status_chip.setObjectName("StatusChip")
        layout.addWidget(self._status_chip)

        return bar

    def _create_pages(self):
        """延迟导入并创建所有页面"""
        from gui.pages.welcome_page import WelcomePage
        from gui.pages.import_page import ImportPage
        from gui.pages.clean_page import CleanPage
        from gui.pages.lda_page import LDAPage
        from gui.pages.stm_page import STMPage
        from gui.pages.compare_page import ComparePage
        from gui.pages.export_page import ExportPage

        pages_map = {
            "welcome": WelcomePage,
            "import": ImportPage,
            "clean": CleanPage,
            "lda": LDAPage,
            "stm": STMPage,
            "compare": ComparePage,
            "export": ExportPage,
        }

        for name, PageClass in pages_map.items():
            page = PageClass(main_window=self)
            self._pages[name] = page
            self.stack.addWidget(page)

    def _connect_signals(self):
        log_signals.message.connect(self._on_log_message)

    @Slot(str, str)
    def _on_log_message(self, level: str, message: str):
        level_map = {
            "DEBUG": "info",
            "INFO": "info",
            "WARNING": "warning",
            "ERROR": "error",
            "CRITICAL": "error",
        }
        self.status_bar_widget.set_status(message.split("] ")[-1], level_map.get(level, "info"))

    def _switch_page(self, name: str):
        if name in self._pages:
            self.stack.setCurrentWidget(self._pages[name])
            self.nav_bar.set_active(name)
            # 通知页面激活
            page = self._pages[name]
            if hasattr(page, "on_page_activated"):
                page.on_page_activated()

    def update_header_status(self):
        """刷新顶部状态芯片"""
        state = get_state()
        self._status_chip.setText(state.get_status_text())
        self._project_label.setText(state.project_name)

    def update_nav_states(self):
        """根据流程状态更新导航可用性"""
        state = get_state()
        self.nav_bar.update_step_states(
            imported=state.step_imported,
            merged=state.step_merged,
            cleaned=state.step_cleaned,
            lda_done=state.step_lda_done,
            stm_done=state.step_stm_done,
        )

    def navigate_to(self, name: str):
        """公共方法：切换到指定页面"""
        self._switch_page(name)

    def set_busy(self, busy: bool, label: str = "处理中..."):
        """设置全局忙碌状态"""
        if busy:
            self.status_bar_widget.set_indeterminate(label)
        else:
            self.status_bar_widget.hide_progress()
