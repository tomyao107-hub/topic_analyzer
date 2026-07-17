"""
对比分析页
比较不同报刊、年份、文类的主题分布差异
"""
from typing import Optional
import pandas as pd

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QFrame, QComboBox, QSplitter, QScrollArea, QTableWidget,
    QTableWidgetItem, QTabWidget, QTextEdit, QGroupBox,
    QSizePolicy, QMessageBox, QFileDialog
)
from PySide6.QtCore import Qt, Slot

from models.app_state import get_state
from services.compare_service import build_topic_summary
from utils.logger import get_logger

logger = get_logger()


class ComparePage(QWidget):
    def __init__(self, main_window=None, parent=None):
        super().__init__(parent)
        self.mw = main_window
        self._setup_ui()
        self._current_figure = None

    def _setup_ui(self):
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)

        # 顶部标题
        header = QFrame()
        header.setStyleSheet("background: white; border-bottom: 1px solid #E2E8F0;")
        hl = QHBoxLayout(header)
        hl.setContentsMargins(40, 16, 40, 16)
        title = QLabel("⚖️ 对比分析")
        title.setObjectName("PageTitle")
        hl.addWidget(title)
        hl.addStretch()

        self._refresh_btn = QPushButton("  🔄  刷新图表")
        self._refresh_btn.setObjectName("SecondaryButton")
        self._refresh_btn.setCursor(Qt.PointingHandCursor)
        self._refresh_btn.clicked.connect(self._refresh_charts)
        hl.addWidget(self._refresh_btn)
        outer.addWidget(header)

        # 筛选器
        filter_frame = QFrame()
        filter_frame.setStyleSheet("background: #F8FAFC; border-bottom: 1px solid #E2E8F0;")
        fl = QHBoxLayout(filter_frame)
        fl.setContentsMargins(40, 12, 40, 12)
        fl.setSpacing(20)

        fl.addWidget(QLabel("报刊："))
        self._newspaper_combo = QComboBox()
        self._newspaper_combo.addItem("全部")
        self._newspaper_combo.setFixedWidth(160)
        fl.addWidget(self._newspaper_combo)

        fl.addWidget(QLabel("年份："))
        self._year_combo = QComboBox()
        self._year_combo.addItem("全部")
        self._year_combo.setFixedWidth(100)
        fl.addWidget(self._year_combo)

        fl.addWidget(QLabel("文类："))
        self._genre_combo = QComboBox()
        self._genre_combo.addItem("全部")
        self._genre_combo.setFixedWidth(120)
        fl.addWidget(self._genre_combo)

        fl.addWidget(QLabel("主题："))
        self._topic_combo = QComboBox()
        self._topic_combo.addItem("全部")
        self._topic_combo.setFixedWidth(180)
        fl.addWidget(self._topic_combo)

        fl.addWidget(QLabel("模型："))
        self._model_combo = QComboBox()
        self._model_combo.addItems(["自动", "LDA", "STM"])
        self._model_combo.setFixedWidth(90)
        fl.addWidget(self._model_combo)

        fl.addWidget(QLabel("横轴："))
        self._axis_combo = QComboBox()
        self._axis_combo.addItem("报刊", "newspaper")
        self._axis_combo.addItem("年份", "pub_year")
        self._axis_combo.addItem("时间序号", "time_index")
        self._axis_combo.addItem("文类", "genre")
        self._axis_combo.addItem("主导主题", "dominant_topic")
        self._axis_combo.setFixedWidth(110)
        fl.addWidget(self._axis_combo)

        fl.addWidget(QLabel("纵轴："))
        self._metric_combo = QComboBox()
        self._metric_combo.addItem("全部主题", "__all__")
        self._metric_combo.setFixedWidth(140)
        fl.addWidget(self._metric_combo)

        fl.addWidget(QLabel("图表："))
        self._chart_type_combo = QComboBox()
        self._chart_type_combo.addItem("柱状图", "bar")
        self._chart_type_combo.addItem("折线图", "line")
        self._chart_type_combo.setFixedWidth(100)
        fl.addWidget(self._chart_type_combo)

        self._export_chart_btn = QPushButton("  🖼  导出当前图表")
        self._export_chart_btn.setObjectName("SecondaryButton")
        self._export_chart_btn.setCursor(Qt.PointingHandCursor)
        self._export_chart_btn.clicked.connect(self._export_current_chart)
        fl.addWidget(self._export_chart_btn)

        fl.addStretch()
        outer.addWidget(filter_frame)

        # 主体
        splitter = QSplitter(Qt.Vertical)

        # 上：图表区
        chart_tabs = QTabWidget()

        # Tab 1: 报刊主题对比图
        self._newspaper_chart_widget = QWidget()
        self._newspaper_chart_layout = QVBoxLayout(self._newspaper_chart_widget)
        self._newspaper_chart_placeholder = self._make_empty("运行 LDA 或 STM 后，点击「刷新图表」显示报刊主题对比")
        self._newspaper_chart_layout.addWidget(self._newspaper_chart_placeholder)
        chart_tabs.addTab(self._newspaper_chart_widget, "报刊主题对比")

        # Tab 2: 年份趋势图
        self._year_chart_widget = QWidget()
        self._year_chart_layout = QVBoxLayout(self._year_chart_widget)
        self._year_chart_placeholder = self._make_empty("显示主题随年份的变化趋势")
        self._year_chart_layout.addWidget(self._year_chart_placeholder)
        chart_tabs.addTab(self._year_chart_widget, "年份趋势")

        # Tab 3: 文类对比
        self._genre_chart_widget = QWidget()
        self._genre_chart_layout = QVBoxLayout(self._genre_chart_widget)
        self._genre_chart_placeholder = self._make_empty("显示不同文类的主题分布差异")
        self._genre_chart_layout.addWidget(self._genre_chart_placeholder)
        chart_tabs.addTab(self._genre_chart_widget, "文类对比")

        splitter.addWidget(chart_tabs)

        # 下：代表文章 + 原文查看
        bottom = QSplitter(Qt.Horizontal)

        # 代表文章表
        articles_frame = QFrame()
        articles_frame.setObjectName("Card")
        af = QVBoxLayout(articles_frame)
        af.setContentsMargins(16, 12, 16, 12)
        af.setSpacing(8)

        art_title = QLabel("📋 主题代表文章")
        art_title.setObjectName("SectionTitle")
        af.addWidget(art_title)

        self._articles_table = QTableWidget()
        self._articles_table.setAlternatingRowColors(True)
        self._articles_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self._articles_table.setSelectionBehavior(QTableWidget.SelectRows)
        self._articles_table.itemClicked.connect(self._on_article_clicked)
        af.addWidget(self._articles_table)
        bottom.addWidget(articles_frame)

        # 原文查看
        text_frame = QFrame()
        text_frame.setObjectName("Card")
        tf = QVBoxLayout(text_frame)
        tf.setContentsMargins(16, 12, 16, 12)
        tf.setSpacing(8)

        text_title = QLabel("📖 原文查看")
        text_title.setObjectName("SectionTitle")
        tf.addWidget(text_title)

        self._meta_labels = QLabel("点击左侧文章查看原文")
        self._meta_labels.setStyleSheet("color: #94A3B8; font-size: 12px;")
        tf.addWidget(self._meta_labels)

        self._text_view = QTextEdit()
        self._text_view.setReadOnly(True)
        self._text_view.setStyleSheet(
            "font-size: 14px; line-height: 1.8; color: #1E293B; "
            "border: none; background: #FAFAFA; padding: 8px;"
        )
        tf.addWidget(self._text_view)
        bottom.addWidget(text_frame)

        bottom.setSizes([500, 500])
        splitter.addWidget(bottom)
        splitter.setSizes([400, 300])

        outer.addWidget(splitter, 1)

    def _make_empty(self, text: str) -> QLabel:
        l = QLabel(text)
        l.setAlignment(Qt.AlignCenter)
        l.setStyleSheet("color: #94A3B8; font-size: 14px; padding: 40px;")
        return l

    def on_page_activated(self):
        """激活时刷新筛选器选项"""
        state = get_state()
        self._topic_combo.clear()
        self._topic_combo.addItem("全部")
        self._newspaper_combo.clear()
        self._newspaper_combo.addItem("全部")
        self._year_combo.clear()
        self._year_combo.addItem("全部")
        self._genre_combo.clear()
        self._genre_combo.addItem("全部")

        topics = state.lda_topics or state.stm_topics
        if topics:
            for t in topics:
                self._topic_combo.addItem(t["label"][:40], t["topic_id"])

        if hasattr(self, "_metric_combo"):
            current_metric = self._metric_combo.currentData()
            self._metric_combo.clear()
            self._metric_combo.addItem("全部主题", "__all__")
            topics_for_metric = state.lda_topics or state.stm_topics
            if topics_for_metric:
                for t in topics_for_metric:
                    self._metric_combo.addItem(t["label"][:40], f"topic_{t['topic_id']}")
            idx = self._metric_combo.findData(current_metric)
            if idx >= 0:
                self._metric_combo.setCurrentIndex(idx)

        df = state.merged_df
        if df is not None:
            if "newspaper" in df.columns:
                for n in sorted(df["newspaper"].dropna().unique()):
                    self._newspaper_combo.addItem(str(n))
            if "pub_year" in df.columns:
                for y in sorted(df["pub_year"].dropna().unique()):
                    # 历史报刊常见非数字年份（如“民國二十四年”），不能强制 int()。
                    try:
                        label = str(int(float(y)))
                    except (TypeError, ValueError):
                        label = str(y).strip()
                    if label:
                        self._year_combo.addItem(label)
            if "genre" in df.columns:
                for g in sorted(df["genre"].dropna().unique()):
                    self._genre_combo.addItem(str(g))

        self._load_representative_articles()

    def _refresh_charts(self):
        self._draw_newspaper_chart()
        self._draw_year_chart()
        self._draw_genre_chart()

    def _get_doc_topics_df(self) -> Optional[pd.DataFrame]:
        return self._get_selected_doc_topics_df()

    def _get_selected_doc_topics_df(self) -> Optional[pd.DataFrame]:
        state = get_state()
        model = self._model_combo.currentText() if hasattr(self, "_model_combo") else "自动"
        if model == "LDA":
            return state.lda_doc_topics
        if model == "STM":
            return state.stm_doc_topics
        return state.lda_doc_topics if state.lda_doc_topics is not None else state.stm_doc_topics

    def _replace_layout_with_message(self, layout, message: str):
        while layout.count():
            item = layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        layout.addWidget(self._make_empty(message))
        self._current_figure = None

    def _draw_configured_chart(self, layout, default_axis: str):
        try:
            from utils.mpl_font import setup_mpl_chinese
            setup_mpl_chinese()
            from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg
            from matplotlib.figure import Figure
            import numpy as np

            df = self._get_selected_doc_topics_df()
            if df is None or df.empty:
                self._replace_layout_with_message(layout, "请先完成 LDA 或 STM 建模")
                return

            axis_field = self._axis_combo.currentData() if hasattr(self, "_axis_combo") else default_axis
            if not axis_field:
                axis_field = default_axis
            if axis_field not in df.columns:
                self._replace_layout_with_message(layout, f"当前结果缺少字段：{axis_field}")
                return

            all_topic_cols = [c for c in df.columns if c.startswith("topic_")]
            metric = self._metric_combo.currentData() if hasattr(self, "_metric_combo") else "__all__"
            topic_cols = all_topic_cols if metric == "__all__" else [metric]
            summary = build_topic_summary(df, axis_field, topic_cols)
            if summary.empty:
                self._replace_layout_with_message(layout, "没有可绘制的数据")
                return

            chart_type = self._chart_type_combo.currentData() if hasattr(self, "_chart_type_combo") else "bar"
            if axis_field in ("pub_year", "time_index") and chart_type == "bar":
                chart_type = "line"

            fig = Figure(figsize=(10, 4), dpi=100, facecolor="#F0F4F8")
            ax = fig.add_subplot(111)
            x_labels = [str(v) for v in summary[axis_field].tolist()]
            x = np.arange(len(x_labels))
            colors = ["#2563EB", "#7C3AED", "#DB2777", "#D97706", "#16A34A",
                      "#0891B2", "#EA580C", "#65A30D"]

            plot_cols = [c for c in topic_cols if c in summary.columns]
            if chart_type == "line":
                for i, col in enumerate(plot_cols[:8]):
                    ax.plot(
                        x, summary[col], marker="o", linewidth=1.6,
                        color=colors[i % len(colors)],
                        label=col.replace("topic_", "主题")
                    )
            else:
                visible_cols = plot_cols[:8]
                width = 0.8 / max(len(visible_cols), 1)
                for i, col in enumerate(visible_cols):
                    offset = (i - len(visible_cols) / 2) * width + width / 2
                    ax.bar(
                        x + offset, summary[col], width=width * 0.9,
                        color=colors[i % len(colors)],
                        label=col.replace("topic_", "主题"), alpha=0.85
                    )

            ax.set_xticks(x)
            ax.set_xticklabels(
                x_labels,
                rotation=30 if len(x_labels) > 6 else 0,
                ha="right" if len(x_labels) > 6 else "center",
                fontsize=9
            )
            ax.set_xlabel(self._axis_combo.currentText() if hasattr(self, "_axis_combo") else axis_field, fontsize=10)
            ax.set_ylabel("平均主题比例", fontsize=10)
            ax.set_title("主题分布对比", fontsize=12)
            if plot_cols:
                ax.legend(fontsize=9, framealpha=0.7)
            ax.spines["top"].set_visible(False)
            ax.spines["right"].set_visible(False)
            ax.set_facecolor("#F8FAFC")
            fig.tight_layout()

            while layout.count():
                item = layout.takeAt(0)
                if item.widget():
                    item.widget().deleteLater()
            layout.addWidget(FigureCanvasQTAgg(fig))
            self._current_figure = fig
        except Exception as e:
            logger.warning(f"绘制配置图表失败：{e}")
            self._replace_layout_with_message(layout, f"图表生成失败：{e}")

    def _draw_newspaper_chart(self):
        """绘制各报刊的平均主题分布对比柱状图"""
        self._draw_configured_chart(self._newspaper_chart_layout, "newspaper")

    def _draw_year_chart(self):
        """绘制主题随年份变化的折线图"""
        self._draw_configured_chart(self._year_chart_layout, "pub_year")

    def _draw_genre_chart(self):
        """绘制文类主题对比图"""
        self._draw_configured_chart(self._genre_chart_layout, "genre")

    def _export_current_chart(self):
        if self._current_figure is None:
            QMessageBox.warning(self, "提示", "请先刷新并生成图表")
            return
        path, _ = QFileDialog.getSaveFileName(
            self,
            "导出当前图表",
            "topic_chart.png",
            "PNG 图片 (*.png)"
        )
        if not path:
            return
        if not path.lower().endswith(".png"):
            path += ".png"
        try:
            self._current_figure.savefig(path, dpi=200, bbox_inches="tight")
            QMessageBox.information(self, "导出成功", f"图表已保存至：\n{path}")
        except Exception as e:
            QMessageBox.critical(self, "导出失败", str(e))

    def _load_representative_articles(self):
        """加载各主题的代表文章"""
        df = self._get_doc_topics_df()
        state = get_state()

        if df is None or state.merged_df is None:
            return

        # 取每个主题的 top-3 代表文章
        topic_cols = [c for c in df.columns if c.startswith("topic_")]
        rows = []
        for tc in topic_cols[:10]:
            top = df.nlargest(3, tc) if tc in df.columns else pd.DataFrame()
            for _, r in top.iterrows():
                entry = {
                    "主题": tc.replace("topic_", "主题"),
                    "文章标题": str(r.get("article_title", ""))[:50],
                    "报刊名": str(r.get("newspaper", "")),
                    "出版日期": str(r.get("pub_date", "")),
                    "文类": str(r.get("genre", "")),
                    "doc_id": str(r.get("doc_id", "")),
                    "主题权重": f"{r.get(tc, 0):.4f}",
                }
                rows.append(entry)

        if not rows:
            return

        display_df = pd.DataFrame(rows)
        cols = ["主题", "文章标题", "报刊名", "出版日期", "文类", "主题权重"]
        display_df = display_df[cols]

        self._articles_table.clear()
        self._articles_table.setColumnCount(len(cols))
        self._articles_table.setRowCount(len(display_df))
        self._articles_table.setHorizontalHeaderLabels(cols)

        for i, row in display_df.iterrows():
            for j, val in enumerate(row):
                item = QTableWidgetItem(str(val))
                item.setFlags(item.flags() & ~Qt.ItemIsEditable)
                # 存储 doc_id 到第一列
                if j == 0:
                    item.setData(Qt.UserRole, rows[i]["doc_id"])
                self._articles_table.setItem(i, j, item)

        self._articles_table.resizeColumnsToContents()

    @Slot(QTableWidgetItem)
    def _on_article_clicked(self, item: QTableWidgetItem):
        """点击文章，查看原文"""
        row = item.row()
        id_item = self._articles_table.item(row, 0)
        if not id_item:
            return

        doc_id = id_item.data(Qt.UserRole)
        state = get_state()
        if state.merged_df is None or not doc_id:
            return

        matches = state.merged_df[state.merged_df["doc_id"] == str(doc_id)]
        if matches.empty:
            return

        r = matches.iloc[0]
        meta_text = "  |  ".join([
            f"📰 {r.get('newspaper', '')}",
            f"📅 {r.get('pub_date', '')}",
            f"✍️ {r.get('author', '')}",
            f"🏷️ {r.get('genre', '')}",
        ])
        self._meta_labels.setText(meta_text)
        self._meta_labels.setStyleSheet("color: #475569; font-size: 12px;")

        # 标题
        title = str(r.get("article_title", "（无标题）"))
        text = str(r.get("text", "（无正文）"))
        self._text_view.setPlainText(f"【{title}】\n\n{text}")
