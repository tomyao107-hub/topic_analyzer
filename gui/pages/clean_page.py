"""
数据清洗页
左侧清洗选项面板，右侧原文/清洗后对比预览
"""
import os
from typing import Optional, List

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QFrame, QCheckBox, QSpinBox, QDoubleSpinBox, QFileDialog,
    QTextEdit, QSplitter, QScrollArea, QGroupBox, QLineEdit,
    QComboBox, QMessageBox, QSizePolicy, QProgressBar
)
from PySide6.QtCore import Qt, QThread, Signal, QObject, Slot
from PySide6.QtGui import QFont

from models.app_state import get_state
from services.clean_service import CleanOptions, clean_text, tokenize_texts, load_stopwords, get_default_stopwords
from utils.logger import get_logger

logger = get_logger()


def build_cleaned_records(merged_df, tokens_list: list, opts: CleanOptions):
    """构造清洗后可导出的记录表。"""
    cleaned_df = merged_df.copy()
    texts = cleaned_df["text"].fillna("").astype(str).tolist()
    cleaned_df["cleaned_text"] = [clean_text(text, opts) for text in texts]
    token_strings = []
    token_counts = []
    for i in range(len(cleaned_df)):
        tokens = tokens_list[i] if i < len(tokens_list) else []
        token_strings.append(" ".join(tokens))
        token_counts.append(len(tokens))
    cleaned_df["tokens"] = token_strings
    cleaned_df["token_count"] = token_counts
    return cleaned_df


class CleanWorker(QObject):
    """后台线程：执行分词"""
    finished = Signal(list, dict)
    error = Signal(str)
    progress = Signal(int, int, str)

    def __init__(self, texts: List[str], opts: CleanOptions, stopwords: set,
                 custom_dict_path: Optional[str]):
        super().__init__()
        self.texts = texts
        self.opts = opts
        self.stopwords = stopwords
        self.custom_dict_path = custom_dict_path

    def run(self):
        try:
            tokens, stats = tokenize_texts(
                self.texts, self.opts, self.stopwords, self.custom_dict_path
            )
            self.finished.emit(tokens, stats)
        except Exception as e:
            self.error.emit(str(e))


class CleanPage(QWidget):
    def __init__(self, main_window=None, parent=None):
        super().__init__(parent)
        self.mw = main_window
        self._thread: Optional[QThread] = None
        self._setup_ui()

    def _setup_ui(self):
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)

        # 标题区
        header = QFrame()
        header.setStyleSheet("background: white; border-bottom: 1px solid #E2E8F0;")
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(40, 20, 40, 20)

        title = QLabel("🧹 数据清洗与预处理")
        title.setObjectName("PageTitle")
        header_layout.addWidget(title)
        header_layout.addStretch()

        self._start_btn = QPushButton("  ▶  开始清洗与分词")
        self._start_btn.setObjectName("PrimaryButton")
        self._start_btn.setCursor(Qt.PointingHandCursor)
        self._start_btn.clicked.connect(self._do_clean)
        header_layout.addWidget(self._start_btn)

        self._next_btn = QPushButton("  📊  前往 LDA 分析  →")
        self._next_btn.setObjectName("SecondaryButton")
        self._next_btn.setCursor(Qt.PointingHandCursor)
        self._next_btn.setEnabled(False)
        self._next_btn.clicked.connect(lambda: self.mw.navigate_to("lda") if self.mw else None)
        header_layout.addWidget(self._next_btn)

        outer.addWidget(header)

        # 主体分割器
        splitter = QSplitter(Qt.Horizontal)
        splitter.setContentsMargins(0, 0, 0, 0)

        # ── 左侧：清洗选项 ────────────────────────────────
        left = QScrollArea()
        left.setWidgetResizable(True)
        left.setFrameShape(QFrame.NoFrame)
        left.setFixedWidth(340)

        left_container = QWidget()
        left_layout = QVBoxLayout(left_container)
        left_layout.setContentsMargins(20, 20, 12, 20)
        left_layout.setSpacing(16)

        # 基础清洗选项
        basic_group = QGroupBox("基础清洗")
        basic_layout = QVBoxLayout(basic_group)
        basic_layout.setSpacing(8)

        self._cb_empty = QCheckBox("去除空文本")
        self._cb_empty.setChecked(True)
        basic_layout.addWidget(self._cb_empty)

        self._cb_dup = QCheckBox("去除重复文章（按正文）")
        self._cb_dup.setChecked(True)
        basic_layout.addWidget(self._cb_dup)

        self._cb_ocr = QCheckBox("OCR 噪声清理（去除乱码符号）")
        self._cb_ocr.setChecked(True)
        basic_layout.addWidget(self._cb_ocr)

        self._cb_punct = QCheckBox("去除标点符号")
        self._cb_punct.setChecked(True)
        basic_layout.addWidget(self._cb_punct)

        self._cb_number = QCheckBox("去除数字")
        self._cb_number.setChecked(True)
        basic_layout.addWidget(self._cb_number)

        self._cb_trad = QCheckBox("繁体转简体（需安装 opencc）")
        self._cb_trad.setChecked(False)
        basic_layout.addWidget(self._cb_trad)

        left_layout.addWidget(basic_group)

        # 词频过滤
        filter_group = QGroupBox("词频过滤")
        filter_layout = QVBoxLayout(filter_group)
        filter_layout.setSpacing(10)

        min_text_row = QHBoxLayout()
        min_text_row.addWidget(QLabel("最短文本长度（字符）"))
        self._min_text_len = QSpinBox()
        self._min_text_len.setRange(1, 500)
        self._min_text_len.setValue(10)
        min_text_row.addWidget(self._min_text_len)
        filter_layout.addLayout(min_text_row)

        min_freq_row = QHBoxLayout()
        min_freq_row.addWidget(QLabel("最小文档频率（词出现于 N 篇）"))
        self._min_doc_freq = QSpinBox()
        self._min_doc_freq.setRange(1, 100)
        self._min_doc_freq.setValue(2)
        min_freq_row.addWidget(self._min_doc_freq)
        filter_layout.addLayout(min_freq_row)

        max_freq_row = QHBoxLayout()
        max_freq_row.addWidget(QLabel("最大文档频率比例"))
        self._max_doc_freq = QDoubleSpinBox()
        self._max_doc_freq.setRange(0.01, 1.0)
        self._max_doc_freq.setSingleStep(0.05)
        self._max_doc_freq.setValue(0.95)
        max_freq_row.addWidget(self._max_doc_freq)
        filter_layout.addLayout(max_freq_row)

        left_layout.addWidget(filter_group)

        # 停用词和词典
        dict_group = QGroupBox("停用词与词典")
        dict_layout = QVBoxLayout(dict_group)
        dict_layout.setSpacing(8)

        self._cb_default_stop = QCheckBox("使用内置中文停用词")
        self._cb_default_stop.setChecked(True)
        self._cb_default_stop.toggled.connect(self._refresh_stopwords_editor)
        dict_layout.addWidget(self._cb_default_stop)

        stop_row = QHBoxLayout()
        self._stop_path_label = QLabel("未加载")
        self._stop_path_label.setStyleSheet("color: #94A3B8; font-size: 11px;")
        stop_row.addWidget(self._stop_path_label, 1)
        load_stop_btn = QPushButton("加载停用词表")
        load_stop_btn.setObjectName("SecondaryButton")
        load_stop_btn.clicked.connect(self._load_stopwords)
        stop_row.addWidget(load_stop_btn)
        dict_layout.addLayout(stop_row)

        editor_label = QLabel("可编辑停用词（每行一词）")
        editor_label.setStyleSheet("color: #475569; font-size: 12px;")
        dict_layout.addWidget(editor_label)

        self._stopwords_edit = QTextEdit()
        self._stopwords_edit.setPlaceholderText("可直接添加、删除停用词；每行一个。")
        self._stopwords_edit.setMaximumHeight(160)
        dict_layout.addWidget(self._stopwords_edit)

        edit_btn_row = QHBoxLayout()
        self._apply_stopwords_btn = QPushButton("应用编辑")
        self._apply_stopwords_btn.setObjectName("SecondaryButton")
        self._apply_stopwords_btn.clicked.connect(self._apply_stopwords_edit)
        edit_btn_row.addWidget(self._apply_stopwords_btn)

        self._reload_stopwords_btn = QPushButton("重载当前停用词")
        self._reload_stopwords_btn.setObjectName("SecondaryButton")
        self._reload_stopwords_btn.clicked.connect(self._refresh_stopwords_editor)
        edit_btn_row.addWidget(self._reload_stopwords_btn)
        dict_layout.addLayout(edit_btn_row)

        self._stopwords_info_label = QLabel("")
        self._stopwords_info_label.setStyleSheet("color: #64748B; font-size: 11px;")
        self._stopwords_info_label.setWordWrap(True)
        dict_layout.addWidget(self._stopwords_info_label)

        dict_row = QHBoxLayout()
        self._dict_path_label = QLabel("未加载")
        self._dict_path_label.setStyleSheet("color: #94A3B8; font-size: 11px;")
        dict_row.addWidget(self._dict_path_label, 1)
        load_dict_btn = QPushButton("加载自定义词典")
        load_dict_btn.setObjectName("SecondaryButton")
        load_dict_btn.clicked.connect(self._load_dict)
        dict_row.addWidget(load_dict_btn)
        dict_layout.addLayout(dict_row)

        left_layout.addWidget(dict_group)

        # 进度
        self._progress_bar = QProgressBar()
        self._progress_bar.setVisible(False)
        left_layout.addWidget(self._progress_bar)

        self._stats_label = QLabel("")
        self._stats_label.setStyleSheet("color: #64748B; font-size: 12px;")
        self._stats_label.setWordWrap(True)
        left_layout.addWidget(self._stats_label)

        left_layout.addStretch()
        left.setWidget(left_container)
        splitter.addWidget(left)

        # ── 右侧：预览 ────────────────────────────────
        right = QWidget()
        right_layout = QVBoxLayout(right)
        right_layout.setContentsMargins(12, 20, 20, 20)
        right_layout.setSpacing(12)

        preview_header = QHBoxLayout()
        preview_title = QLabel("👁 文本对比预览")
        preview_title.setObjectName("SectionTitle")
        preview_header.addWidget(preview_title)
        preview_header.addStretch()

        self._article_combo = QComboBox()
        self._article_combo.setFixedWidth(300)
        self._article_combo.currentIndexChanged.connect(self._update_preview)
        preview_header.addWidget(QLabel("查看第"))
        preview_header.addWidget(self._article_combo)
        preview_header.addWidget(QLabel("篇"))
        right_layout.addLayout(preview_header)

        # 原文
        orig_label = QLabel("原始文本：")
        orig_label.setObjectName("FieldLabel")
        right_layout.addWidget(orig_label)

        self._orig_text = QTextEdit()
        self._orig_text.setReadOnly(True)
        self._orig_text.setPlaceholderText("导入并合并数据后显示原始文本...")
        self._orig_text.setMaximumHeight(200)
        right_layout.addWidget(self._orig_text)

        # 清洗后
        clean_label = QLabel("清洗后文本：")
        clean_label.setObjectName("FieldLabel")
        right_layout.addWidget(clean_label)

        self._clean_text_edit = QTextEdit()
        self._clean_text_edit.setReadOnly(True)
        self._clean_text_edit.setPlaceholderText("清洗完成后显示结果...")
        self._clean_text_edit.setMaximumHeight(200)
        right_layout.addWidget(self._clean_text_edit)

        # 分词结果
        token_label = QLabel("分词结果：")
        token_label.setObjectName("FieldLabel")
        right_layout.addWidget(token_label)

        self._token_text = QTextEdit()
        self._token_text.setReadOnly(True)
        self._token_text.setPlaceholderText("分词完成后显示 token 序列...")
        self._token_text.setMaximumHeight(150)
        right_layout.addWidget(self._token_text)

        splitter.addWidget(right)
        splitter.setStretchFactor(1, 1)
        outer.addWidget(splitter)

    def on_page_activated(self):
        state = get_state()
        self._article_combo.clear()
        if state.merged_df is not None:
            n = min(len(state.merged_df), 300)
            self._article_combo.addItems([str(i + 1) for i in range(n)])
        self._refresh_stopwords_editor()
        self._update_preview()

    def _update_preview(self):
        state = get_state()
        if state.merged_df is None or state.merged_df.empty:
            self._orig_text.clear()
            self._clean_text_edit.clear()
            self._token_text.clear()
            return

        idx = self._article_combo.currentIndex()
        if idx < 0 or idx >= len(state.merged_df):
            idx = 0

        row = state.merged_df.iloc[idx]
        text = str(row.get("text", ""))
        self._orig_text.setPlainText(text[:5000])

        opts = self._build_opts()
        cleaned = clean_text(text, opts)
        self._clean_text_edit.setPlainText(cleaned[:5000])

        if state.tokens_list and idx < len(state.tokens_list):
            self._token_text.setPlainText(" / ".join(state.tokens_list[idx][:200]))
        else:
            self._token_text.clear()

    def _build_opts(self) -> CleanOptions:
        opts = CleanOptions()
        opts.remove_empty = self._cb_empty.isChecked()
        opts.remove_duplicates = self._cb_dup.isChecked()
        opts.ocr_clean = self._cb_ocr.isChecked()
        opts.remove_punct = self._cb_punct.isChecked()
        opts.remove_numbers = self._cb_number.isChecked()
        opts.traditional_to_simplified = self._cb_trad.isChecked()
        opts.min_text_length = self._min_text_len.value()
        opts.min_doc_freq = self._min_doc_freq.value()
        opts.max_doc_freq_ratio = self._max_doc_freq.value()
        return opts

    def _compose_stopwords(self) -> set:
        state = get_state()
        stopwords = set()
        if self._cb_default_stop.isChecked():
            stopwords |= get_default_stopwords()
        if state.stopwords:
            stopwords |= state.stopwords
        return stopwords

    def _refresh_stopwords_editor(self):
        stopwords = sorted(self._compose_stopwords())
        self._stopwords_edit.setPlainText("\n".join(stopwords))
        state = get_state()
        src = "内置停用词"
        if state.stopwords_path:
            src += f" + 外部文件 {os.path.basename(state.stopwords_path)}"
        self._stopwords_info_label.setText(f"当前可编辑停用词共 {len(stopwords)} 个，来源：{src}")

    def _apply_stopwords_edit(self):
        words = {
            line.strip()
            for line in self._stopwords_edit.toPlainText().splitlines()
            if line.strip()
        }
        state = get_state()
        if self._cb_default_stop.isChecked():
            base = get_default_stopwords()
            state.stopwords = words - base
        else:
            state.stopwords = words
        self._stopwords_info_label.setText(f"已应用编辑，共 {len(words)} 个停用词")
        logger.info(f"停用词编辑已应用：当前总数 {len(words)}")

    def _load_stopwords(self):
        path, _ = QFileDialog.getOpenFileName(self, "加载停用词表", "", "文本文件 (*.txt)")
        if path:
            words = load_stopwords(path)
            state = get_state()
            state.stopwords = words
            state.stopwords_path = path
            self._stop_path_label.setText(f"✅ {os.path.basename(path)} ({len(words)} 词)")
            self._refresh_stopwords_editor()

    def _load_dict(self):
        path, _ = QFileDialog.getOpenFileName(self, "加载自定义词典", "", "文本文件 (*.txt)")
        if path:
            get_state().custom_dict_path = path
            self._dict_path_label.setText(f"✅ {os.path.basename(path)}")

    def _do_clean(self):
        state = get_state()
        if state.merged_df is None:
            QMessageBox.warning(self, "提示", "请先导入并合并数据")
            return

        if "text" not in state.merged_df.columns:
            QMessageBox.warning(
                self, "缺少正文列",
                "合并后的数据缺少 text（正文）列，无法清洗。\n"
                "请返回导入页确认文本表的正文列已被正确识别或手动映射后重新合并。",
            )
            return

        self._apply_stopwords_edit()

        texts = state.merged_df["text"].fillna("").tolist()
        opts = self._build_opts()
        stopwords = self._compose_stopwords()

        self._start_btn.setEnabled(False)
        self._progress_bar.setMaximum(0)
        self._progress_bar.setVisible(True)
        if self.mw:
            self.mw.set_busy(True, "正在分词...")

        self._thread = QThread()
        self._worker = CleanWorker(texts, opts, stopwords, state.custom_dict_path)
        self._worker.moveToThread(self._thread)
        self._thread.started.connect(self._worker.run)
        self._worker.finished.connect(self._on_clean_done)
        self._worker.error.connect(self._on_clean_error)
        self._thread.start()

    @Slot(list, dict)
    def _on_clean_done(self, tokens_list: list, stats: dict):
        self._thread.quit()
        self._thread.wait()
        self._worker.deleteLater()
        self._thread.deleteLater()
        self._progress_bar.setVisible(False)
        self._start_btn.setEnabled(True)

        state = get_state()
        state.tokens_list = tokens_list
        if state.merged_df is not None:
            opts = self._build_opts()
            state.cleaned_df = build_cleaned_records(state.merged_df, tokens_list, opts)
        state.step_cleaned = True

        self._stats_label.setText(
            f"✅ 分词完成\n"
            f"  有效文档：{stats['non_empty_docs']} / {stats['total_docs']}\n"
            f"  总 token 数：{stats['total_tokens']:,}\n"
            f"  唯一词汇量：{stats['unique_words']:,}"
        )

        self._next_btn.setEnabled(True)
        self._update_preview()

        if self.mw:
            self.mw.set_busy(False)
            self.mw.update_nav_states()

        logger.info("分词完成")

    @Slot(str)
    def _on_clean_error(self, msg: str):
        self._thread.quit()
        self._thread.wait()
        self._worker.deleteLater()
        self._thread.deleteLater()
        self._progress_bar.setVisible(False)
        self._start_btn.setEnabled(True)
        if self.mw:
            self.mw.set_busy(False)
        QMessageBox.critical(self, "清洗失败", msg)
