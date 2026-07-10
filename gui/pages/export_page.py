"""
导出与日志页
勾选式批量导出，显示处理日志
"""
import os
import json
from datetime import datetime

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QFrame, QCheckBox, QFileDialog, QTextEdit, QSplitter,
    QGroupBox, QScrollArea, QMessageBox, QLineEdit
)
from PySide6.QtCore import Qt, Slot
from PySide6.QtGui import QTextCharFormat, QColor, QFont, QTextCursor

from models.app_state import get_state
from utils.logger import log_signals, get_logger

logger = get_logger()


class ExportPage(QWidget):
    def __init__(self, main_window=None, parent=None):
        super().__init__(parent)
        self.mw = main_window
        self._setup_ui()
        log_signals.message.connect(self._append_log)

    def _setup_ui(self):
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)

        # 顶部标题
        header = QFrame()
        header.setStyleSheet("background: white; border-bottom: 1px solid #E2E8F0;")
        hl = QHBoxLayout(header)
        hl.setContentsMargins(40, 16, 40, 16)
        title = QLabel("📤 导出结果")
        title.setObjectName("PageTitle")
        hl.addWidget(title)
        hl.addStretch()

        self._export_btn = QPushButton("  💾  导出选中项目")
        self._export_btn.setObjectName("PrimaryButton")
        self._export_btn.setCursor(Qt.PointingHandCursor)
        self._export_btn.clicked.connect(self._do_export)
        hl.addWidget(self._export_btn)

        outer.addWidget(header)

        # 主体分割
        splitter = QSplitter(Qt.Horizontal)

        # ── 左侧：导出选项 ──────────────────────────────
        left = QScrollArea()
        left.setWidgetResizable(True)
        left.setFrameShape(QFrame.NoFrame)
        left.setFixedWidth(360)

        left_cont = QWidget()
        left_layout = QVBoxLayout(left_cont)
        left_layout.setContentsMargins(20, 20, 12, 20)
        left_layout.setSpacing(16)

        # 导出目录
        dir_group = QGroupBox("导出目录")
        dir_layout = QVBoxLayout(dir_group)

        dir_row = QHBoxLayout()
        self._dir_edit = QLineEdit()
        self._dir_edit.setPlaceholderText("选择保存目录...")
        self._dir_edit.setText(os.path.expanduser("~"))
        dir_row.addWidget(self._dir_edit)
        browse_btn = QPushButton("浏览")
        browse_btn.setObjectName("SecondaryButton")
        browse_btn.clicked.connect(self._browse_dir)
        dir_row.addWidget(browse_btn)
        dir_layout.addLayout(dir_row)
        left_layout.addWidget(dir_group)

        # 可导出内容清单
        items_group = QGroupBox("选择导出内容")
        items_layout = QVBoxLayout(items_group)
        items_layout.setSpacing(8)

        self._checkboxes = {}

        export_items = [
            ("merged_data",     "📊 合并后的主数据集 (merged_data.csv)"),
            ("cleaned_records", "🧾 清洗后的元数据和文本记录 (cleaned_records.csv)"),
            ("cleaned_corpus",  "🧹 分词结果语料 (tokens_corpus.txt)"),
            ("lda_topic_word",  "📋 LDA 主题-词矩阵 (lda_topic_word.csv)"),
            ("lda_doc_topic",   "📋 LDA 文档-主题矩阵 (lda_doc_topic.csv)"),
            ("lda_coherence",   "📐 LDA Coherence 指标 (lda_coherence.json)"),
            ("stm_topic_word",  "📋 STM 主题-词矩阵 (stm_topic_word.csv)"),
            ("stm_doc_topic",   "📋 STM 文档-主题矩阵 (stm_doc_topic.csv)"),
            ("stm_prevalence",  "📈 STM 主题 Prevalence (stm_topic_prevalence.csv)"),
            ("session_config",  "⚙️ 会话配置 (session_config.json)"),
        ]

        for key, label in export_items:
            cb = QCheckBox(label)
            cb.setChecked(True)
            cb.setStyleSheet("font-size: 12px; padding: 2px 0;")
            items_layout.addWidget(cb)
            self._checkboxes[key] = cb

        select_row = QHBoxLayout()
        all_btn = QPushButton("全选")
        all_btn.setObjectName("TextButton")
        all_btn.clicked.connect(lambda: [cb.setChecked(True) for cb in self._checkboxes.values()])
        none_btn = QPushButton("全不选")
        none_btn.setObjectName("TextButton")
        none_btn.clicked.connect(lambda: [cb.setChecked(False) for cb in self._checkboxes.values()])
        select_row.addWidget(all_btn)
        select_row.addWidget(none_btn)
        select_row.addStretch()
        items_layout.addLayout(select_row)

        left_layout.addWidget(items_group)

        # 项目名配置
        proj_group = QGroupBox("项目配置")
        proj_layout = QVBoxLayout(proj_group)
        proj_name_row = QHBoxLayout()
        proj_name_row.addWidget(QLabel("项目名称："))
        self._proj_name_edit = QLineEdit()
        self._proj_name_edit.setPlaceholderText("报刊主题分析项目")
        proj_name_row.addWidget(self._proj_name_edit)
        proj_layout.addLayout(proj_name_row)
        left_layout.addWidget(proj_group)

        left_layout.addStretch()
        left.setWidget(left_cont)
        splitter.addWidget(left)

        # ── 右侧：日志面板 ──────────────────────────────
        right = QWidget()
        right_layout = QVBoxLayout(right)
        right_layout.setContentsMargins(8, 20, 24, 20)
        right_layout.setSpacing(8)

        log_header = QHBoxLayout()
        log_title = QLabel("📋 处理日志")
        log_title.setObjectName("SectionTitle")
        log_header.addWidget(log_title)
        log_header.addStretch()

        clear_btn = QPushButton("清除日志")
        clear_btn.setObjectName("TextButton")
        clear_btn.clicked.connect(lambda: self._log_text.clear())
        log_header.addWidget(clear_btn)
        right_layout.addLayout(log_header)

        self._log_text = QTextEdit()
        self._log_text.setReadOnly(True)
        self._log_text.setStyleSheet(
            "font-family: 'Courier New', Consolas, monospace; "
            "font-size: 12px; "
            "background-color: #0F172A; "
            "color: #CBD5E1; "
            "border-radius: 8px; "
            "padding: 12px; "
            "line-height: 1.5;"
        )
        right_layout.addWidget(self._log_text)

        splitter.addWidget(right)
        splitter.setSizes([360, 740])
        outer.addWidget(splitter, 1)

    def _browse_dir(self):
        d = QFileDialog.getExistingDirectory(self, "选择导出目录")
        if d:
            self._dir_edit.setText(d)

    def _do_export(self):
        out_dir = self._dir_edit.text().strip()
        if not out_dir:
            QMessageBox.warning(self, "提示", "请选择导出目录")
            return

        os.makedirs(out_dir, exist_ok=True)
        state = get_state()

        # 更新项目名
        proj_name = self._proj_name_edit.text().strip()
        if proj_name:
            state.project_name = proj_name
        state.output_dir = out_dir

        exported = []
        errors = []

        # 合并数据集
        if self._checkboxes["merged_data"].isChecked() and state.merged_df is not None:
            try:
                p = os.path.join(out_dir, "merged_data.csv")
                state.merged_df.to_csv(p, index=False, encoding="utf-8-sig")
                exported.append("merged_data.csv")
            except Exception as e:
                errors.append(f"合并数据集：{e}")

        if self._checkboxes["cleaned_records"].isChecked():
            if state.cleaned_df is not None:
                try:
                    p = os.path.join(out_dir, "cleaned_records.csv")
                    state.cleaned_df.to_csv(p, index=False, encoding="utf-8-sig")
                    exported.append("cleaned_records.csv")
                except Exception as e:
                    errors.append(f"清洗后记录：{e}")
            else:
                errors.append("清洗后记录：尚未完成清洗与分词")

        # 分词语料
        if self._checkboxes["cleaned_corpus"].isChecked() and state.tokens_list:
            try:
                p = os.path.join(out_dir, "tokens_corpus.txt")
                with open(p, "w", encoding="utf-8") as f:
                    for tokens in state.tokens_list:
                        f.write(" ".join(tokens) + "\n")
                exported.append("tokens_corpus.txt")
            except Exception as e:
                errors.append(f"分词语料：{e}")

        # LDA 结果
        if self._checkboxes["lda_topic_word"].isChecked() and state.lda_topics:
            try:
                import pandas as pd
                rows = []
                for t in state.lda_topics:
                    for rank, (word, prob) in enumerate(t["words"]):
                        rows.append({"topic_id": t["topic_id"], "rank": rank+1,
                                     "word": word, "probability": round(prob, 6)})
                p = os.path.join(out_dir, "lda_topic_word.csv")
                pd.DataFrame(rows).to_csv(p, index=False, encoding="utf-8-sig")
                exported.append("lda_topic_word.csv")
            except Exception as e:
                errors.append(f"LDA topic_word：{e}")

        if self._checkboxes["lda_doc_topic"].isChecked() and state.lda_doc_topics is not None:
            try:
                p = os.path.join(out_dir, "lda_doc_topic.csv")
                state.lda_doc_topics.to_csv(p, index=False, encoding="utf-8-sig")
                exported.append("lda_doc_topic.csv")
            except Exception as e:
                errors.append(f"LDA doc_topic：{e}")

        if self._checkboxes["lda_coherence"].isChecked() and state.lda_coherence is not None:
            try:
                p = os.path.join(out_dir, "lda_coherence.json")
                with open(p, "w", encoding="utf-8") as f:
                    json.dump({"coherence_c_v": state.lda_coherence}, f,
                              ensure_ascii=False, indent=2)
                exported.append("lda_coherence.json")
            except Exception as e:
                errors.append(f"LDA Coherence：{e}")

        # STM 结果
        if self._checkboxes["stm_topic_word"].isChecked() and state.stm_topics:
            try:
                import pandas as pd
                rows = []
                for t in state.stm_topics:
                    for rank, (word, _) in enumerate(t["words"]):
                        rows.append({"topic_id": t["topic_id"], "rank": rank+1, "word": word})
                p = os.path.join(out_dir, "stm_topic_word.csv")
                pd.DataFrame(rows).to_csv(p, index=False, encoding="utf-8-sig")
                exported.append("stm_topic_word.csv")
            except Exception as e:
                errors.append(f"STM topic_word：{e}")

        if self._checkboxes["stm_doc_topic"].isChecked() and state.stm_doc_topics is not None:
            try:
                p = os.path.join(out_dir, "stm_doc_topic.csv")
                state.stm_doc_topics.to_csv(p, index=False, encoding="utf-8-sig")
                exported.append("stm_doc_topic.csv")
            except Exception as e:
                errors.append(f"STM doc_topic：{e}")

        if self._checkboxes["stm_prevalence"].isChecked() and state.stm_prevalence is not None:
            try:
                p = os.path.join(out_dir, "stm_topic_prevalence.csv")
                state.stm_prevalence.to_csv(p, index=False, encoding="utf-8-sig")
                exported.append("stm_topic_prevalence.csv")
            except Exception as e:
                errors.append(f"STM prevalence：{e}")

        # 会话配置
        if self._checkboxes["session_config"].isChecked():
            try:
                config = {
                    "project_name": state.project_name,
                    "exported_at": datetime.now().isoformat(),
                    "article_count": state.get_article_count(),
                    "lda_done": state.step_lda_done,
                    "stm_done": state.step_stm_done,
                    "output_dir": out_dir,
                }
                p = os.path.join(out_dir, "session_config.json")
                with open(p, "w", encoding="utf-8") as f:
                    json.dump(config, f, ensure_ascii=False, indent=2)
                exported.append("session_config.json")
            except Exception as e:
                errors.append(f"会话配置：{e}")

        # 汇总
        msg = f"✅ 已导出 {len(exported)} 个文件至：\n{out_dir}\n\n"
        msg += "\n".join([f"  • {f}" for f in exported])
        if errors:
            msg += f"\n\n⚠️ 以下项目导出失败：\n" + "\n".join([f"  • {e}" for e in errors])

        logger.info(f"导出完成：{len(exported)} 个文件")
        QMessageBox.information(self, "导出完成", msg)

    @Slot(str, str)
    def _append_log(self, level: str, message: str):
        colors = {
            "DEBUG": "#64748B",
            "INFO": "#CBD5E1",
            "WARNING": "#FCD34D",
            "ERROR": "#FCA5A5",
            "CRITICAL": "#F87171",
        }
        color = colors.get(level, "#CBD5E1")
        cursor = self._log_text.textCursor()
        cursor.movePosition(QTextCursor.End)

        fmt = QTextCharFormat()
        fmt.setForeground(QColor(color))
        cursor.setCharFormat(fmt)
        cursor.insertText(message + "\n")
        self._log_text.setTextCursor(cursor)
        self._log_text.ensureCursorVisible()

    def on_page_activated(self):
        pass
