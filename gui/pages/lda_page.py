"""
LDA 分析页
左侧参数设置，右侧结果展示（主题卡片 + 图表 + 文档主题表）
"""
import os
import json
from typing import List, Dict, Optional

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QFrame, QSpinBox, QDoubleSpinBox, QSplitter, QScrollArea,
    QGroupBox, QTableWidget, QTableWidgetItem, QMessageBox,
    QFileDialog, QCheckBox, QComboBox, QTabWidget, QSizePolicy, QProgressBar
)
from PySide6.QtCore import Qt, QThread, Signal, QObject, Slot

from models.app_state import get_state
from utils.logger import get_logger

logger = get_logger()


def filter_docs_by_genre(merged_df, tokens_list: list, genre: str):
    """按文类过滤文档和对应 tokens。"""
    if not genre or genre == "全部文类" or "genre" not in merged_df.columns:
        return merged_df.copy(), list(tokens_list)

    mask = merged_df["genre"].fillna("").astype(str) == str(genre)
    indices = list(merged_df.index[mask])
    filtered_df = merged_df.loc[indices].reset_index(drop=True)
    filtered_tokens = [tokens_list[i] for i in indices if i < len(tokens_list)]
    return filtered_df, filtered_tokens


class LDAWorker(QObject):
    finished = Signal(object, object, object, list, object, float)
    error = Signal(str)
    progress = Signal(str)

    def __init__(self, tokens_list, merged_df, k, passes, iterations, seed,
                 min_df, max_df_ratio):
        super().__init__()
        self.tokens_list = tokens_list
        self.merged_df = merged_df
        self.k = k
        self.passes = passes
        self.iterations = iterations
        self.seed = seed
        self.min_df = min_df
        self.max_df_ratio = max_df_ratio

    def run(self):
        try:
            from services.lda_service import (
                build_corpus, train_lda, get_topics,
                get_doc_topics, compute_coherence
            )

            self.progress.emit("正在构建词典和语料...")
            dictionary, corpus, filtered_tokens = build_corpus(
                self.tokens_list,
                min_doc_freq=self.min_df,
                max_doc_freq_ratio=self.max_df_ratio,
            )

            # 记录有效文档索引
            valid_indices = [
                i for i, t in enumerate(self.tokens_list) if len(t) >= 3
            ]

            self.progress.emit(f"开始训练 LDA（K={self.k}）...")
            model = train_lda(
                corpus, dictionary,
                num_topics=self.k,
                passes=self.passes,
                iterations=self.iterations,
                random_state=self.seed,
            )

            self.progress.emit("提取主题关键词...")
            topics = get_topics(model, n_words=20)

            self.progress.emit("计算文档主题分布...")
            doc_topics = get_doc_topics(model, corpus, self.merged_df, valid_indices)

            self.progress.emit("计算 Coherence...")
            coherence = compute_coherence(model, corpus, dictionary, filtered_tokens)

            self.finished.emit(model, dictionary, corpus, topics, doc_topics, coherence)

        except Exception as e:
            import traceback
            self.error.emit(f"{e}\n{traceback.format_exc()}")


class LDAPage(QWidget):
    def __init__(self, main_window=None, parent=None):
        super().__init__(parent)
        self.mw = main_window
        self._thread: Optional[QThread] = None
        self._setup_ui()

    def _setup_ui(self):
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)

        # 顶部标题栏
        header = QFrame()
        header.setStyleSheet("background: white; border-bottom: 1px solid #E2E8F0;")
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(40, 16, 40, 16)

        title = QLabel("📊 LDA 主题建模")
        title.setObjectName("PageTitle")
        header_layout.addWidget(title)
        header_layout.addStretch()

        self._train_btn = QPushButton("  ▶  开始训练")
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

        # 主体分割
        splitter = QSplitter(Qt.Horizontal)

        # ── 左侧参数 ──────────────────────────────────
        left = QScrollArea()
        left.setWidgetResizable(True)
        left.setFrameShape(QFrame.NoFrame)
        left.setFixedWidth(280)

        left_cont = QWidget()
        left_layout = QVBoxLayout(left_cont)
        left_layout.setContentsMargins(16, 20, 8, 20)
        left_layout.setSpacing(16)

        params_group = QGroupBox("模型参数")
        params_layout = QVBoxLayout(params_group)
        params_layout.setSpacing(10)

        def add_param(layout, label, widget):
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
        add_param(params_layout, "主题数 K", self._k_spin)

        self._passes_spin = QSpinBox()
        self._passes_spin.setRange(1, 500)
        self._passes_spin.setValue(20)
        self._passes_spin.setFixedWidth(80)
        add_param(params_layout, "训练轮数 (passes)", self._passes_spin)

        self._iter_spin = QSpinBox()
        self._iter_spin.setRange(50, 2000)
        self._iter_spin.setValue(400)
        self._iter_spin.setFixedWidth(80)
        add_param(params_layout, "迭代次数", self._iter_spin)

        self._seed_spin = QSpinBox()
        self._seed_spin.setRange(0, 9999)
        self._seed_spin.setValue(42)
        self._seed_spin.setFixedWidth(80)
        add_param(params_layout, "随机种子", self._seed_spin)

        self._min_df_spin = QSpinBox()
        self._min_df_spin.setRange(1, 50)
        self._min_df_spin.setValue(2)
        self._min_df_spin.setFixedWidth(80)
        add_param(params_layout, "最小文档频率", self._min_df_spin)

        self._max_df_spin = QDoubleSpinBox()
        self._max_df_spin.setRange(0.01, 1.0)
        self._max_df_spin.setSingleStep(0.05)
        self._max_df_spin.setValue(0.95)
        self._max_df_spin.setFixedWidth(80)
        add_param(params_layout, "最大文档频率", self._max_df_spin)

        left_layout.addWidget(params_group)

        filter_group = QGroupBox("文类筛选")
        filter_layout = QVBoxLayout(filter_group)
        self._genre_combo = QComboBox()
        self._genre_combo.addItem("全部文类")
        filter_layout.addWidget(self._genre_combo)
        hint = QLabel("仅使用所选文类的文档训练 LDA")
        hint.setStyleSheet("color: #94A3B8; font-size: 11px;")
        hint.setWordWrap(True)
        filter_layout.addWidget(hint)
        left_layout.addWidget(filter_group)

        self._progress_bar = QProgressBar()
        self._progress_bar.setMaximum(0)
        self._progress_bar.setVisible(False)
        left_layout.addWidget(self._progress_bar)

        self._progress_label = QLabel("")
        self._progress_label.setStyleSheet("color: #64748B; font-size: 11px;")
        self._progress_label.setWordWrap(True)
        left_layout.addWidget(self._progress_label)

        self._coherence_label = QLabel("")
        self._coherence_label.setObjectName("SuccessBadge")
        self._coherence_label.setVisible(False)
        left_layout.addWidget(self._coherence_label)

        left_layout.addStretch()
        left.setWidget(left_cont)
        splitter.addWidget(left)

        # ── 右侧结果 ──────────────────────────────────
        right = QWidget()
        right_layout = QVBoxLayout(right)
        right_layout.setContentsMargins(8, 20, 24, 20)
        right_layout.setSpacing(0)

        self._result_tabs = QTabWidget()
        right_layout.addWidget(self._result_tabs)

        # Tab 1: 主题关键词
        self._topics_widget = QScrollArea()
        self._topics_widget.setWidgetResizable(True)
        self._topics_widget.setFrameShape(QFrame.NoFrame)
        self._topics_container = QWidget()
        self._topics_layout = QVBoxLayout(self._topics_container)
        self._topics_layout.setContentsMargins(8, 12, 8, 12)
        self._topics_layout.setSpacing(12)
        self._topics_layout.addWidget(self._make_empty_state("运行 LDA 后显示主题关键词"))
        self._topics_widget.setWidget(self._topics_container)
        self._result_tabs.addTab(self._topics_widget, "主题关键词")

        # Tab 2: 主题分布图（matplotlib）
        self._chart_widget = QWidget()
        chart_layout = QVBoxLayout(self._chart_widget)
        chart_layout.setContentsMargins(8, 8, 8, 8)

        self._chart_placeholder = QLabel("训练完成后显示主题分布图")
        self._chart_placeholder.setAlignment(Qt.AlignCenter)
        self._chart_placeholder.setStyleSheet("color: #94A3B8; font-size: 14px; padding: 60px;")
        chart_layout.addWidget(self._chart_placeholder)

        self._pyldavis_btn = QPushButton("  🌐  在浏览器中打开 pyLDAvis")
        self._pyldavis_btn.setObjectName("SecondaryButton")
        self._pyldavis_btn.setCursor(Qt.PointingHandCursor)
        self._pyldavis_btn.setEnabled(False)
        self._pyldavis_btn.clicked.connect(self._open_pyldavis)
        chart_layout.addWidget(self._pyldavis_btn)

        self._result_tabs.addTab(self._chart_widget, "可视化")

        # Tab 3: 文档-主题表
        self._doc_table = QTableWidget()
        self._doc_table.setAlternatingRowColors(True)
        self._doc_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self._result_tabs.addTab(self._doc_table, "文档主题分布")

        splitter.addWidget(right)
        splitter.setSizes([280, 800])
        outer.addWidget(splitter, 1)

    def _make_empty_state(self, text: str) -> QLabel:
        l = QLabel(text)
        l.setAlignment(Qt.AlignCenter)
        l.setStyleSheet("color: #94A3B8; font-size: 14px; padding: 60px;")
        return l

    def _do_train(self):
        state = get_state()
        if state.tokens_list is None:
            QMessageBox.warning(self, "提示", "请先完成数据清洗与分词")
            return

        genre = self._genre_combo.currentText() if hasattr(self, "_genre_combo") else "全部文类"
        train_df, train_tokens = filter_docs_by_genre(state.merged_df, state.tokens_list, genre)
        if train_df.empty or not train_tokens:
            QMessageBox.warning(self, "提示", "当前文类没有可用于建模的文档")
            return
        if sum(1 for tokens in train_tokens if len(tokens) >= 3) == 0:
            QMessageBox.warning(self, "提示", "当前文类没有有效分词文档，请调整文类或清洗参数")
            return

        self._train_btn.setEnabled(False)
        self._progress_bar.setVisible(True)
        self._progress_label.setText("准备中...")
        self._coherence_label.setVisible(False)
        if self.mw:
            self.mw.set_busy(True, "LDA 训练中...")

        self._thread = QThread()
        self._worker = LDAWorker(
            tokens_list=train_tokens,
            merged_df=train_df,
            k=self._k_spin.value(),
            passes=self._passes_spin.value(),
            iterations=self._iter_spin.value(),
            seed=self._seed_spin.value(),
            min_df=self._min_df_spin.value(),
            max_df_ratio=self._max_df_spin.value(),
        )
        self._worker.moveToThread(self._thread)
        self._thread.started.connect(self._worker.run)
        self._worker.finished.connect(self._on_train_done)
        self._worker.error.connect(self._on_train_error)
        self._worker.progress.connect(lambda s: self._progress_label.setText(s))
        self._thread.start()

    @Slot(object, object, object, list, object, float)
    def _on_train_done(self, model, dictionary, corpus, topics, doc_topics, coherence):
        self._thread.quit()
        self._thread.wait()
        self._worker.deleteLater()
        self._thread.deleteLater()

        state = get_state()
        state.lda_model = model
        state.lda_dictionary = dictionary
        state.lda_corpus = corpus
        state.lda_topics = topics
        state.lda_doc_topics = doc_topics
        state.lda_coherence = coherence
        state.step_lda_done = True

        self._progress_bar.setVisible(False)
        self._progress_label.setText("✅ 训练完成")
        self._train_btn.setEnabled(True)
        self._export_btn.setEnabled(True)
        self._pyldavis_btn.setEnabled(True)

        if coherence and coherence == coherence:  # NaN check
            self._coherence_label.setText(f"Coherence (c_v): {coherence:.4f}")
            self._coherence_label.setVisible(True)

        self._render_topics(topics)
        self._render_doc_table(doc_topics)
        self._render_chart(topics)

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
        QMessageBox.critical(self, "训练失败", msg[:500])

    def _render_topics(self, topics: List[Dict]):
        # 清空旧内容
        while self._topics_layout.count():
            item = self._topics_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        for t in topics:
            card = QFrame()
            card.setObjectName("Card")
            card_layout = QVBoxLayout(card)
            card_layout.setContentsMargins(16, 12, 16, 12)
            card_layout.setSpacing(6)

            header = QHBoxLayout()
            tid_label = QLabel(f"主题 {t['topic_id']+1}")
            tid_label.setObjectName("SectionTitle")
            header.addWidget(tid_label)
            header.addStretch()
            card_layout.addLayout(header)

            words_text = "   ".join(
                [f"{w}（{p:.3f}）" for w, p in t["words"][:10]]
            )
            words_label = QLabel(words_text)
            words_label.setStyleSheet("color: #1E293B; font-size: 13px; line-height: 1.5;")
            words_label.setWordWrap(True)
            card_layout.addWidget(words_label)

            self._topics_layout.addWidget(card)

        self._topics_layout.addStretch()

    def _render_doc_table(self, doc_topics):
        if doc_topics is None or doc_topics.empty:
            return

        display = doc_topics.head(200)
        self._doc_table.clear()
        self._doc_table.setColumnCount(len(display.columns))
        self._doc_table.setRowCount(len(display))
        self._doc_table.setHorizontalHeaderLabels([str(c) for c in display.columns])

        for i, row in display.iterrows():
            for j, val in enumerate(row):
                if isinstance(val, float):
                    text = f"{val:.4f}"
                else:
                    text = str(val)[:60]
                item = QTableWidgetItem(text)
                item.setFlags(item.flags() & ~Qt.ItemIsEditable)
                self._doc_table.setItem(i, j, item)

        self._doc_table.resizeColumnsToContents()

    def _render_chart(self, topics: List[Dict]):
        """嵌入 matplotlib 主题词概率柱状图"""
        try:
            from utils.mpl_font import setup_mpl_chinese
            setup_mpl_chinese()
            import matplotlib.pyplot as plt
            from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg
            from matplotlib.figure import Figure

            fig = Figure(figsize=(8, 4), dpi=100, facecolor="#F0F4F8")
            ax = fig.add_subplot(111)

            # 显示前5个主题的 top5 词
            colors = ["#2563EB", "#7C3AED", "#DB2777", "#D97706", "#16A34A"]
            n_show = min(5, len(topics))
            n_words = 5

            x = range(n_words)
            width = 0.15

            for i in range(n_show):
                t = topics[i]
                probs = [p for _, p in t["words"][:n_words]]
                words = [w for w, _ in t["words"][:n_words]]
                offset = (i - n_show / 2) * width
                bars = ax.bar([xi + offset for xi in x], probs,
                              width=width * 0.9, color=colors[i],
                              label=f"主题{i+1}", alpha=0.85)

            if n_show > 0:
                ax.set_xticks(range(n_words))
                ax.set_xticklabels([w for w, _ in topics[0]["words"][:n_words]],
                                   fontsize=10)
                ax.set_ylabel("概率", fontsize=10)
                ax.set_title("各主题 Top 5 关键词概率", fontsize=12, color="#1E293B")
                ax.legend(fontsize=9, framealpha=0.7)
                ax.spines["top"].set_visible(False)
                ax.spines["right"].set_visible(False)
                ax.set_facecolor("#F8FAFC")
                fig.tight_layout()

            canvas = FigureCanvasQTAgg(fig)

            # 清理旧的图表组件
            layout = self._chart_widget.layout()
            while layout.count():
                item = layout.takeAt(0)
                if item.widget():
                    item.widget().deleteLater()

            layout.addWidget(canvas)

        except ImportError:
            self._chart_placeholder.setText("请安装 matplotlib 以显示图表：pip install matplotlib")

    def _open_pyldavis(self):
        state = get_state()
        if not state.lda_model:
            return

        out_dir = state.output_dir or os.path.expanduser("~")
        try:
            from services.lda_service import open_pyldavis
            open_pyldavis(state.lda_model, state.lda_corpus, state.lda_dictionary, out_dir)
        except ImportError as e:
            QMessageBox.warning(self, "提示", str(e))
        except Exception as e:
            QMessageBox.critical(self, "错误", str(e))

    def _do_export(self):
        state = get_state()
        if not state.lda_topics:
            return

        out_dir = QFileDialog.getExistingDirectory(self, "选择导出目录")
        if not out_dir:
            return

        state.output_dir = out_dir
        try:
            from services.lda_service import save_lda_results
            save_lda_results(
                state.lda_topics,
                state.lda_doc_topics,
                state.lda_coherence or float("nan"),
                out_dir
            )
            QMessageBox.information(self, "导出成功", f"LDA 结果已保存至：\n{out_dir}")
        except Exception as e:
            QMessageBox.critical(self, "导出失败", str(e))

    def on_page_activated(self):
        state = get_state()
        if not hasattr(self, "_genre_combo"):
            return
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
