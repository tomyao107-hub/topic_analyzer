"""
首页 - 欢迎页，展示分析流程
"""
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QFrame, QSizePolicy
)
from PySide6.QtCore import Qt


class WelcomePage(QWidget):
    def __init__(self, main_window=None, parent=None):
        super().__init__(parent)
        self.mw = main_window
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(48, 40, 48, 40)
        layout.setSpacing(32)

        # 标题
        title = QLabel("欢迎使用历史报刊主题分析工具")
        title.setObjectName("PageTitle")
        title.setAlignment(Qt.AlignCenter)
        layout.addWidget(title)

        subtitle = QLabel(
            "本工具专为数字人文研究设计，支持中文历史报刊文本的 LDA 与 STM 主题建模分析"
        )
        subtitle.setObjectName("PageSubtitle")
        subtitle.setAlignment(Qt.AlignCenter)
        subtitle.setWordWrap(True)
        layout.addWidget(subtitle)

        # 分析流程卡片
        flow_frame = QFrame()
        flow_frame.setObjectName("Card")
        flow_layout = QVBoxLayout(flow_frame)
        flow_layout.setContentsMargins(32, 24, 32, 24)
        flow_layout.setSpacing(8)

        flow_title = QLabel("📋 分析流程")
        flow_title.setObjectName("SectionTitle")
        flow_layout.addWidget(flow_title)

        flow_layout.addSpacing(8)

        steps = [
            ("1", "导入两张表", "分别导入元数据表（标题、作者、日期等）和文本表（正文内容）", "📥"),
            ("2", "检查与合并", "通过文档编号自动合并，查看未匹配记录", "🔗"),
            ("3", "清洗与分词", "OCR 噪声清理、jieba 中文分词、停用词过滤", "🧹"),
            ("4", "主题建模", "运行 LDA 或 STM（结构主题模型），设置主题数与协变量", "📊"),
            ("5", "对比分析", "比较不同报刊、年份、文类之间的主题差异", "⚖️"),
            ("6", "导出结果", "导出 CSV 数据、图表和模型报告", "📤"),
        ]

        steps_layout = QHBoxLayout()
        steps_layout.setSpacing(0)

        for i, (num, title_s, desc, icon) in enumerate(steps):
            step_widget = self._make_step_card(num, icon, title_s, desc)
            steps_layout.addWidget(step_widget)
            if i < len(steps) - 1:
                arrow = QLabel("→")
                arrow.setStyleSheet("color: #CBD5E1; font-size: 20px; padding: 0 4px;")
                arrow.setAlignment(Qt.AlignCenter)
                steps_layout.addWidget(arrow)

        flow_layout.addLayout(steps_layout)
        layout.addWidget(flow_frame)

        # 快速开始按钮
        btn_layout = QHBoxLayout()
        btn_layout.setAlignment(Qt.AlignCenter)

        start_btn = QPushButton("  📥  开始导入数据")
        start_btn.setObjectName("PrimaryButton")
        start_btn.setFixedWidth(200)
        start_btn.setCursor(Qt.PointingHandCursor)
        start_btn.clicked.connect(lambda: self.mw.navigate_to("import") if self.mw else None)
        btn_layout.addWidget(start_btn)

        layout.addLayout(btn_layout)

        # 功能特色
        features_frame = QFrame()
        features_frame.setObjectName("Card")
        feat_layout = QHBoxLayout(features_frame)
        feat_layout.setContentsMargins(32, 20, 32, 20)
        feat_layout.setSpacing(32)

        features = [
            ("🀄", "中文优化", "使用 jieba 分词，内置中文停用词，支持繁简转换和自定义词典"),
            ("📐", "真实 STM", "通过 rpy2 调用 R stm 包，实现真正的结构主题模型，支持协变量"),
            ("📊", "可视化", "主题分布图、pyLDAvis 交互可视化、报刊对比图表"),
            ("💾", "完整导出", "导出 CSV 结果、图表 PNG、模型报告和会话配置"),
        ]

        for icon, ftitle, fdesc in features:
            fw = QWidget()
            fl = QVBoxLayout(fw)
            fl.setSpacing(4)
            fi = QLabel(icon)
            fi.setStyleSheet("font-size: 28px;")
            fl.addWidget(fi)
            ft = QLabel(ftitle)
            ft.setStyleSheet("font-weight: bold; color: #1E293B; font-size: 13px;")
            fl.addWidget(ft)
            fd = QLabel(fdesc)
            fd.setStyleSheet("color: #64748B; font-size: 12px;")
            fd.setWordWrap(True)
            fl.addWidget(fd)
            feat_layout.addWidget(fw, 1)

        layout.addWidget(features_frame)
        layout.addStretch()

    def _make_step_card(self, num: str, icon: str, title: str, desc: str) -> QWidget:
        w = QWidget()
        w.setFixedWidth(140)
        l = QVBoxLayout(w)
        l.setContentsMargins(8, 8, 8, 8)
        l.setSpacing(4)

        badge = QLabel(f"  {icon}  ")
        badge.setStyleSheet(
            "background-color: #EFF6FF; color: #2563EB; border-radius: 20px;"
            "font-size: 20px; padding: 8px; min-width: 44px;"
        )
        badge.setAlignment(Qt.AlignCenter)
        l.addWidget(badge, 0, Qt.AlignCenter)

        t = QLabel(title)
        t.setStyleSheet("font-weight: bold; color: #1E293B; font-size: 13px;")
        t.setAlignment(Qt.AlignCenter)
        l.addWidget(t)

        d = QLabel(desc)
        d.setStyleSheet("color: #94A3B8; font-size: 11px;")
        d.setWordWrap(True)
        d.setAlignment(Qt.AlignCenter)
        l.addWidget(d)

        return w

    def on_page_activated(self):
        pass
