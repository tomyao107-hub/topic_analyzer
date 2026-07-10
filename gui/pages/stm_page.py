"""
STM 分析页
通过 rpy2 调用 R stm 包，支持协变量配置
"""
import contextvars
import os
from typing import Optional

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QFrame, QSpinBox, QLineEdit, QComboBox, QSplitter,
    QScrollArea, QGroupBox, QTableWidget, QTableWidgetItem,
    QMessageBox, QFileDialog, QCheckBox, QTabWidget,
    QTextEdit, QProgressBar, QListWidget, QListWidgetItem
)
from PySide6.QtCore import Qt, QThread, Signal, QObject, Slot

from gui.pages.lda_page import filter_docs_by_genre
from models.app_state import get_state
from utils.logger import get_logger

logger = get_logger()


class STMWorker(QObject):
    finished = Signal(object, list, object, object)
    error = Signal(str)
    progress = Signal(str)

    def __init__(self, merged_df, tokens_list, k, formula, content, seed, max_em, ctx=None):
        super().__init__()
        self.merged_df = merged_df
        self.tokens_list = tokens_list
        self.k = k
        self.formula = formula
        self.content = content
        self.seed = seed
        self.max_em = max_em
        self.ctx = ctx

    def run(self):
        try:
            if self.ctx is not None:
                self.ctx.run(self._run_impl)
            else:
                self._run_impl()
        except Exception as e:
            import traceback
            self.error.emit(f"{e}\n{traceback.format_exc()}")

    def _run_impl(self):
        from services.stm_service import train_stm
        r_model, topics, doc_topics, prevalence = train_stm(
            merged_df=self.merged_df,
            tokens_list=self.tokens_list,
            num_topics=self.k,
            prevalence_formula=self.formula,
            content_covariate=self.content or None,
            seed=self.seed,
            max_em_its=self.max_em,
        )
        self.finished.emit(r_model, topics, doc_topics, prevalence)



class STMPage(QWidget):
    def __init__(self, main_window=None, parent=None):
        super().__init__(parent)
        self.mw = main_window
        self._r_available: Optional[bool] = None
        self._thread: Optional[QThread] = None
        self._setup_ui()

    def _setup_ui(self):
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)

        # 顶部标题
        header = QFrame()
        header.setStyleSheet("background: white; border-bottom: 1px solid #E2E8F0;")
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(40, 16, 40, 16)

        title = QLabel("🔬 STM 结构主题建模")
        title.setObjectName("PageTitle")
        header_layout.addWidget(title)
        header_layout.addStretch()

        self._check_r_btn = QPushButton("  🔍  检查 R 环境")
        self._check_r_btn.setObjectName("SecondaryButton")
        self._check_r_btn.setCursor(Qt.PointingHandCursor)
        self._check_r_btn.clicked.connect(self._check_r)
        header_layout.addWidget(self._check_r_btn)

        self._train_btn = QPushButton("  ▶  开始训练 STM")
        self._train_btn.setObjectName("PrimaryButton")
        self._train_btn.setCursor(Qt.PointingHandCursor)
        self._train_btn.clicked.connect(self._do_train)
        header_layout.addWidget(self._train_btn)

        self._export_btn = QPushButton("  💾  导出结果")
        self._export_btn.setObjectName("SecondaryButton")
        self._export_btn.setCursor(Qt.PointingHandCursor)
        self._export_btn.setEnabled(False)
        self._export_btn.clicked.connect(self._do_export)
        header_layout.addWidget(self._export_btn)

        outer.addWidget(header)

        # R 环境提示横幅
        self._r_banner = QFrame()
        self._r_banner.setStyleSheet(
            "background: #FFFBEB; border-bottom: 1px solid #FDE68A;"
        )
        banner_layout = QHBoxLayout(self._r_banner)
        banner_layout.setContentsMargins(40, 10, 40, 10)
        self._r_banner_label = QLabel(
            "⚠️  STM 需要 R + stm 包 + rpy2。请点击右上角「检查 R 环境」按钮确认安装。"
        )
        self._r_banner_label.setStyleSheet("color: #92400E; font-size: 12px;")
        self._r_banner_label.setWordWrap(True)
        banner_layout.addWidget(self._r_banner_label, 1)
        outer.addWidget(self._r_banner)

        # 主体分割
        splitter = QSplitter(Qt.Horizontal)

        # ── 左侧配置 ──────────────────────────────────
        left = QScrollArea()
        left.setWidgetResizable(True)
        left.setFrameShape(QFrame.NoFrame)
        left.setFixedWidth(320)

        left_cont = QWidget()
        left_layout = QVBoxLayout(left_cont)
        left_layout.setContentsMargins(16, 20, 8, 20)
        left_layout.setSpacing(16)

        # 模型参数
        params_group = QGroupBox("模型参数")
        params_layout = QVBoxLayout(params_group)
        params_layout.setSpacing(10)

        def add_row(layout, label, widget):
            row = QHBoxLayout()
            l = QLabel(label)
            l.setStyleSheet("color: #475569; font-size: 12px;")
            row.addWidget(l, 1)
            row.addWidget(widget)
            layout.addLayout(row)

        self._k_spin = QSpinBox()
        self._k_spin.setRange(2, 100)
        self._k_spin.setValue(10)
        self._k_spin.setFixedWidth(80)
        add_row(params_layout, "主题数 K", self._k_spin)

        self._max_em_spin = QSpinBox()
        self._max_em_spin.setRange(10, 500)
        self._max_em_spin.setValue(75)
        self._max_em_spin.setFixedWidth(80)
        add_row(params_layout, "最大 EM 迭代", self._max_em_spin)

        self._seed_spin = QSpinBox()
        self._seed_spin.setRange(0, 9999)
        self._seed_spin.setValue(42)
        self._seed_spin.setFixedWidth(80)
        add_row(params_layout, "随机种子", self._seed_spin)

        left_layout.addWidget(params_group)

        filter_group = QGroupBox("文类筛选")
        filter_layout = QVBoxLayout(filter_group)
        self._genre_combo = QComboBox()
        self._genre_combo.addItem("全部文类")
        filter_layout.addWidget(self._genre_combo)
        hint = QLabel("仅使用所选文类的文档训练 STM")
        hint.setStyleSheet("color: #94A3B8; font-size: 11px;")
        hint.setWordWrap(True)
        filter_layout.addWidget(hint)
        left_layout.addWidget(filter_group)

        # 协变量配置
        covar_group = QGroupBox("Prevalence 协变量")
        covar_layout = QVBoxLayout(covar_group)
        covar_layout.setSpacing(8)

        covar_hint = QLabel(
            "从合并数据的元数据字段中选择协变量\n（如报刊名、年份、文类）"
        )
        covar_hint.setStyleSheet("color: #94A3B8; font-size: 11px;")
        covar_hint.setWordWrap(True)
        covar_layout.addWidget(covar_hint)

        self._covar_list = QListWidget()
        self._covar_list.setMaximumHeight(120)
        self._covar_list.setSelectionMode(QListWidget.MultiSelection)
        covar_layout.addWidget(self._covar_list)

        covar_status_hint = QLabel("灰色字段表示当前不可用于 prevalence，悬停可查看原因")
        covar_status_hint.setStyleSheet("color: #94A3B8; font-size: 11px;")
        covar_status_hint.setWordWrap(True)
        covar_layout.addWidget(covar_status_hint)

        formula_label = QLabel("Prevalence 公式：")
        formula_label.setStyleSheet("color: #475569; font-size: 12px; margin-top: 4px;")
        covar_layout.addWidget(formula_label)

        self._formula_edit = QLineEdit()
        self._formula_edit.setPlaceholderText("~ newspaper + s(time_index)")
        self._formula_edit.setText("~ newspaper")
        covar_layout.addWidget(self._formula_edit)

        formula_help = QLabel(
            "示例：\n"
            "  ~ 1\n"
            "  ~ newspaper\n"
            "  ~ newspaper + genre\n"
            "  ~ newspaper + s(pub_year)\n"
            "  ~ newspaper + s(time_index)\n"
            "注意：字段必须存在，且不能全空、全相同或只有空字符串。\n"
            "（s() 表示平滑样条）"
        )
        formula_help.setStyleSheet("color: #94A3B8; font-size: 11px; padding: 4px;")
        covar_layout.addWidget(formula_help)

        left_layout.addWidget(covar_group)

        # Content 协变量（可选）
        content_group = QGroupBox("Content 协变量（可选）")
        content_layout = QVBoxLayout(content_group)

        content_hint = QLabel("指定影响词语使用的协变量（通常为二分类变量）")
        content_hint.setStyleSheet("color: #94A3B8; font-size: 11px;")
        content_hint.setWordWrap(True)
        content_layout.addWidget(content_hint)

        self._content_edit = QLineEdit()
        self._content_edit.setPlaceholderText("留空则不使用（如：newspaper）")
        content_layout.addWidget(self._content_edit)

        left_layout.addWidget(content_group)

        # 进度
        self._progress_bar = QProgressBar()
        self._progress_bar.setMaximum(0)
        self._progress_bar.setVisible(False)
        left_layout.addWidget(self._progress_bar)

        self._progress_label = QLabel("")
        self._progress_label.setStyleSheet("color: #64748B; font-size: 11px;")
        self._progress_label.setWordWrap(True)
        left_layout.addWidget(self._progress_label)

        left_layout.addStretch()
        left.setWidget(left_cont)
        splitter.addWidget(left)

        # ── 右侧结果 ──────────────────────────────────
        right = QWidget()
        right_layout = QVBoxLayout(right)
        right_layout.setContentsMargins(8, 20, 24, 20)

        self._result_tabs = QTabWidget()
        right_layout.addWidget(self._result_tabs)

        # Tab 1: 主题关键词
        self._topics_scroll = QScrollArea()
        self._topics_scroll.setWidgetResizable(True)
        self._topics_scroll.setFrameShape(QFrame.NoFrame)
        self._topics_container = QWidget()
        self._topics_layout = QVBoxLayout(self._topics_container)
        self._topics_layout.setContentsMargins(8, 12, 8, 12)
        self._topics_layout.addWidget(self._make_empty("训练 STM 后显示主题关键词"))
        self._topics_scroll.setWidget(self._topics_container)
        self._result_tabs.addTab(self._topics_scroll, "主题关键词")

        # Tab 2: 协变量效应
        self._covar_widget = QWidget()
        covar_result_layout = QVBoxLayout(self._covar_widget)
        self._covar_chart_placeholder = self._make_empty("训练完成后显示协变量-主题关系图")
        covar_result_layout.addWidget(self._covar_chart_placeholder)
        self._result_tabs.addTab(self._covar_widget, "协变量效应")

        # Tab 3: 文档主题分布
        self._doc_table = QTableWidget()
        self._doc_table.setAlternatingRowColors(True)
        self._doc_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self._result_tabs.addTab(self._doc_table, "文档主题分布")

        splitter.addWidget(right)
        splitter.setSizes([320, 780])
        outer.addWidget(splitter, 1)

    def _make_empty(self, text: str) -> QLabel:
        l = QLabel(text)
        l.setAlignment(Qt.AlignCenter)
        l.setStyleSheet("color: #94A3B8; font-size: 14px; padding: 60px;")
        return l

    def on_page_activated(self):
        """页面激活时刷新可用协变量列表"""
        from services.stm_service import _analyze_stm_column

        state = get_state()
        if hasattr(self, "_genre_combo"):
            current = self._genre_combo.currentText()
            self._genre_combo.clear()
            self._genre_combo.addItem("全部文类")
            if state.merged_df is not None and "genre" in state.merged_df.columns:
                genres = sorted({
                    str(g) for g in state.merged_df["genre"].dropna().unique()
                    if str(g).strip()
                })
                self._genre_combo.addItems(genres)
            idx = self._genre_combo.findText(current)
            if idx >= 0:
                self._genre_combo.setCurrentIndex(idx)

        self._covar_list.clear()
        if state.merged_df is not None:
            meta_cols = [c for c in state.merged_df.columns
                         if c not in ("text", "doc_id")]
            for col in meta_cols:
                ok, reason = _analyze_stm_column(state.merged_df, col)
                label = str(col) if ok else f"{col}（不可用：{reason}）"
                item = QListWidgetItem(label)
                item.setData(Qt.UserRole, str(col))
                if ok:
                    item.setToolTip(f"字段可用于 STM 协变量：{col}")
                else:
                    item.setToolTip(f"字段当前不可用于 STM 协变量：{reason}")
                    item.setFlags(item.flags() & ~Qt.ItemIsEnabled & ~Qt.ItemIsSelectable)
                    item.setForeground(Qt.gray)
                self._covar_list.addItem(item)
                if ok and col in ("newspaper", "genre", "pub_year", "time_index"):
                    item.setSelected(True)

    def _check_r(self):
        from services.stm_service import check_r_environment
        self._r_banner_label.setText("⏳  正在检查 R 环境...")
        ok, msg = check_r_environment()
        self._r_available = ok
        get_state().r_available = ok

        if ok:
            self._r_banner.setStyleSheet(
                "background: #F0FDF4; border-bottom: 1px solid #BBF7D0;"
            )
            self._r_banner_label.setStyleSheet("color: #166534; font-size: 12px;")
            self._r_banner_label.setText(f"✅  R 环境就绪：{msg}")
        else:
            self._r_banner.setStyleSheet(
                "background: #FEF2F2; border-bottom: 1px solid #FECACA;"
            )
            self._r_banner_label.setStyleSheet("color: #991B1B; font-size: 12px;")
            short_msg = msg.split("\n")[0]
            self._r_banner_label.setText(f"❌  {short_msg}  （详情请查看控制台输出）")
            # 显示完整安装指引
            QMessageBox.warning(self, "R 环境未就绪", msg[:1000])

    def _do_train(self):
        state = get_state()
        if state.tokens_list is None:
            QMessageBox.warning(self, "提示", "请先完成数据清洗与分词")
            return

        if self._r_available is None:
            self._check_r()
        if not self._r_available:
            QMessageBox.critical(self, "R 环境未就绪",
                                 "请先安装 R、stm 包和 rpy2，然后点击「检查 R 环境」")
            return

        formula = self._formula_edit.text().strip() or "~ newspaper"
        content = self._content_edit.text().strip()

        genre = self._genre_combo.currentText() if hasattr(self, "_genre_combo") else "全部文类"
        train_df, train_tokens = filter_docs_by_genre(state.merged_df, state.tokens_list, genre)
        if train_df.empty or not train_tokens:
            QMessageBox.warning(self, "提示", "当前文类没有可用于建模的文档")
            return
        if sum(1 for tokens in train_tokens if len(tokens) >= 2) == 0:
            QMessageBox.warning(self, "提示", "当前文类没有有效分词文档，请调整文类或清洗参数")
            return

        self._train_btn.setEnabled(False)
        self._progress_bar.setVisible(True)
        self._progress_label.setText("启动 STM 训练...")
        if self.mw:
            self.mw.set_busy(True, "STM 训练中（可能需要数分钟）...")

        self._thread = QThread()
        try:
            import rpy2.robjects as ro
            _ = ro.default_converter
        except Exception:
            pass
        worker_ctx = contextvars.copy_context()
        self._worker = STMWorker(
            merged_df=train_df,
            tokens_list=train_tokens,
            k=self._k_spin.value(),
            formula=formula,
            content=content,
            seed=self._seed_spin.value(),
            max_em=self._max_em_spin.value(),
            ctx=worker_ctx,
        )
        self._worker.moveToThread(self._thread)
        self._thread.started.connect(self._worker.run)
        self._worker.finished.connect(self._on_train_done)
        self._worker.error.connect(self._on_train_error)
        self._worker.progress.connect(lambda s: self._progress_label.setText(s))
        self._thread.start()

    @Slot(object, list, object, object)
    def _on_train_done(self, r_model, topics, doc_topics, prevalence):
        self._thread.quit()
        self._thread.wait()
        self._worker.deleteLater()
        self._thread.deleteLater()

        state = get_state()
        state.stm_result = r_model
        state.stm_topics = topics
        state.stm_doc_topics = doc_topics
        state.stm_prevalence = prevalence
        state.step_stm_done = True

        self._progress_bar.setVisible(False)
        self._progress_label.setText("✅ STM 训练完成")
        self._train_btn.setEnabled(True)
        self._export_btn.setEnabled(True)

        self._render_topics(topics)
        if doc_topics is not None and not doc_topics.empty:
            self._render_doc_table(doc_topics)
        if prevalence is not None and not prevalence.empty:
            self._render_prevalence_chart(prevalence)

        if self.mw:
            self.mw.set_busy(False)
            self.mw.update_nav_states()

    @Slot(str)
    def _on_train_error(self, msg: str):
        self._thread.quit()
        self._thread.wait()
        self._worker.deleteLater()
        self._thread.deleteLater()
        self._progress_bar.setVisible(False)
        self._train_btn.setEnabled(True)
        if self.mw:
            self.mw.set_busy(False)
        QMessageBox.critical(self, "STM 训练失败", msg[:800])

    def _render_topics(self, topics):
        while self._topics_layout.count():
            item = self._topics_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        for t in topics:
            card = QFrame()
            card.setObjectName("Card")
            cl = QVBoxLayout(card)
            cl.setContentsMargins(16, 12, 16, 12)
            cl.setSpacing(6)

            header = QHBoxLayout()
            tid = QLabel(f"主题 {t['topic_id']+1}")
            tid.setObjectName("SectionTitle")
            header.addWidget(tid)
            header.addStretch()
            cl.addLayout(header)

            words_text = "   ".join([w for w, _ in t["words"][:10]])
            wl = QLabel(words_text)
            wl.setStyleSheet("color: #1E293B; font-size: 13px;")
            wl.setWordWrap(True)
            cl.addWidget(wl)

            self._topics_layout.addWidget(card)

        self._topics_layout.addStretch()

    def _render_doc_table(self, doc_topics):
        display = doc_topics.head(200)
        self._doc_table.clear()
        self._doc_table.setColumnCount(len(display.columns))
        self._doc_table.setRowCount(len(display))
        self._doc_table.setHorizontalHeaderLabels([str(c) for c in display.columns])

        for i, row in display.iterrows():
            for j, val in enumerate(row):
                text = f"{val:.4f}" if isinstance(val, float) else str(val)[:60]
                item = QTableWidgetItem(text)
                item.setFlags(item.flags() & ~Qt.ItemIsEditable)
                self._doc_table.setItem(i, j, item)

        self._doc_table.resizeColumnsToContents()

    def _render_prevalence_chart(self, prevalence):
        """绘制协变量效应条形图"""
        try:
            from utils.mpl_font import setup_mpl_chinese
            setup_mpl_chinese()
            from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg
            from matplotlib.figure import Figure
            import numpy as np

            layout = self._covar_widget.layout()

            # 移除旧内容
            while layout.count():
                item = layout.takeAt(0)
                if item.widget():
                    item.widget().deleteLater()

            # 按协变量绘图
            covar_cols = [c for c in prevalence.columns
                          if c not in ("topic_id", "topic_label", "prevalence_estimate")]
            if not covar_cols:
                layout.addWidget(self._make_empty("协变量效应图（数据不足）"))
                return

            covar_col = covar_cols[0]
            topics = prevalence["topic_label"].unique()
            levels = prevalence[covar_col].unique()

            fig = Figure(figsize=(8, 5), dpi=100, facecolor="#F0F4F8")
            ax = fig.add_subplot(111)

            x = np.arange(len(topics))
            width = 0.8 / max(len(levels), 1)
            colors = ["#2563EB", "#7C3AED", "#DB2777", "#D97706", "#16A34A"]

            for i, level in enumerate(levels[:5]):
                sub = prevalence[prevalence[covar_col] == level]
                vals = [sub[sub["topic_label"] == t]["prevalence_estimate"].mean()
                        for t in topics]
                ax.bar(x + i * width, vals, width=width * 0.9,
                       color=colors[i % len(colors)], label=str(level), alpha=0.85)

            ax.set_xticks(x + width * len(levels) / 2)
            ax.set_xticklabels(topics, rotation=45, ha="right", fontsize=9)
            ax.set_ylabel("主题 Prevalence", fontsize=10)
            ax.set_title(f"按 {covar_col} 分组的主题 Prevalence", fontsize=12)
            ax.legend(fontsize=9)
            ax.spines["top"].set_visible(False)
            ax.spines["right"].set_visible(False)
            ax.set_facecolor("#F8FAFC")
            fig.tight_layout()

            canvas = FigureCanvasQTAgg(fig)
            layout.addWidget(canvas)

        except Exception as e:
            logger.warning(f"绘制协变量图失败：{e}")

    def _do_export(self):
        state = get_state()
        if not state.stm_topics:
            return

        out_dir = QFileDialog.getExistingDirectory(self, "选择导出目录")
        if not out_dir:
            return

        state.output_dir = out_dir
        try:
            from services.stm_service import save_stm_results
            save_stm_results(
                state.stm_topics,
                state.stm_doc_topics,
                state.stm_prevalence,
                out_dir
            )
            QMessageBox.information(self, "导出成功", f"STM 结果已保存至：\n{out_dir}")
        except Exception as e:
            QMessageBox.critical(self, "导出失败", str(e))
