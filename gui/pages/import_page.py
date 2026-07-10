"""
数据导入页
支持拖拽上传元数据表和文本表，自动识别字段，执行合并
"""
import os
from typing import Optional
import pandas as pd

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QFrame, QFileDialog, QTableWidget, QTableWidgetItem,
    QMessageBox, QScrollArea, QSizePolicy, QGridLayout
)
from PySide6.QtCore import Qt, QThread, Signal, Slot, QObject
from PySide6.QtGui import QDragEnterEvent, QDropEvent

from models.app_state import get_state
from services.data_service import load_file, detect_meta_columns, detect_text_columns, merge_tables
from utils.logger import get_logger

logger = get_logger()


class DropZoneWidget(QFrame):
    """可拖放的文件上传区域"""
    file_dropped = Signal(str)

    def __init__(self, label: str, parent=None):
        super().__init__(parent)
        self.setObjectName("DropZone")
        self.setAcceptDrops(True)
        self.setMinimumHeight(120)
        self._label_text = label
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignCenter)
        layout.setSpacing(8)

        icon = QLabel("📂")
        icon.setStyleSheet("font-size: 28px;")
        icon.setAlignment(Qt.AlignCenter)
        layout.addWidget(icon)

        self._title_label = QLabel(self._label_text)
        self._title_label.setStyleSheet("color: #475569; font-size: 13px; font-weight: bold;")
        self._title_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self._title_label)

        hint = QLabel("拖拽文件到此处，或点击选择文件")
        hint.setStyleSheet("color: #94A3B8; font-size: 12px;")
        hint.setAlignment(Qt.AlignCenter)
        layout.addWidget(hint)

        fmt = QLabel("支持 .csv / .xlsx")
        fmt.setStyleSheet("color: #CBD5E1; font-size: 11px;")
        fmt.setAlignment(Qt.AlignCenter)
        layout.addWidget(fmt)

    def set_loaded(self, filename: str, rows: int, cols: int):
        self.setObjectName("DropZoneActive")
        self.style().unpolish(self)
        self.style().polish(self)
        self._title_label.setText(f"✅ {filename}")
        self._title_label.setStyleSheet("color: #16A34A; font-size: 13px; font-weight: bold;")

    def dragEnterEvent(self, event: QDragEnterEvent):
        if event.mimeData().hasUrls():
            urls = event.mimeData().urls()
            if any(u.toLocalFile().lower().endswith((".csv", ".xlsx", ".xls")) for u in urls):
                event.acceptProposedAction()
                self.setObjectName("DropZoneActive")
                self.style().unpolish(self)
                self.style().polish(self)

    def dragLeaveEvent(self, event):
        self.setObjectName("DropZone")
        self.style().unpolish(self)
        self.style().polish(self)

    def dropEvent(self, event: QDropEvent):
        urls = event.mimeData().urls()
        for url in urls:
            path = url.toLocalFile()
            if path.lower().endswith((".csv", ".xlsx", ".xls")):
                self.file_dropped.emit(path)
                break

    def mousePressEvent(self, event):
        path, _ = QFileDialog.getOpenFileName(
            self, "选择文件", "",
            "数据文件 (*.csv *.xlsx *.xls)"
        )
        if path:
            self.file_dropped.emit(path)


class ImportPage(QWidget):
    def __init__(self, main_window=None, parent=None):
        super().__init__(parent)
        self.mw = main_window
        self._meta_df: Optional[pd.DataFrame] = None
        self._text_df: Optional[pd.DataFrame] = None
        self._setup_ui()

    def _setup_ui(self):
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        outer.addWidget(scroll)

        container = QWidget()
        scroll.setWidget(container)

        layout = QVBoxLayout(container)
        layout.setContentsMargins(40, 32, 40, 32)
        layout.setSpacing(24)

        # 页面标题
        title = QLabel("📥 数据导入")
        title.setObjectName("PageTitle")
        layout.addWidget(title)

        subtitle = QLabel("请分别导入元数据表（报刊基本信息）和文本表（文章正文），系统将自动识别字段并合并。")
        subtitle.setObjectName("PageSubtitle")
        subtitle.setWordWrap(True)
        layout.addWidget(subtitle)

        # 两个上传卡片
        upload_row = QHBoxLayout()
        upload_row.setSpacing(20)

        # 元数据表卡片
        meta_card = self._build_upload_card(
            "元数据表",
            "包含：文档编号、报刊名、出版日期、文章标题、文类等",
            is_meta=True
        )
        upload_row.addWidget(meta_card)

        # 文本表卡片
        text_card = self._build_upload_card(
            "文本表",
            "包含：文档编号、正文文本",
            is_meta=False
        )
        upload_row.addWidget(text_card)

        layout.addLayout(upload_row)

        # 字段映射结果
        self._field_map_frame = QFrame()
        self._field_map_frame.setObjectName("Card")
        field_map_layout = QVBoxLayout(self._field_map_frame)
        field_map_layout.setContentsMargins(24, 16, 24, 16)

        fm_title = QLabel("🗺️ 字段识别结果")
        fm_title.setObjectName("SectionTitle")
        field_map_layout.addWidget(fm_title)

        self._field_map_label = QLabel("请先导入数据文件")
        self._field_map_label.setStyleSheet("color: #94A3B8; font-size: 13px; padding: 8px 0;")
        field_map_layout.addWidget(self._field_map_label)

        layout.addWidget(self._field_map_frame)

        # 数据预览和合并
        preview_card = QFrame()
        preview_card.setObjectName("Card")
        preview_layout = QVBoxLayout(preview_card)
        preview_layout.setContentsMargins(24, 16, 24, 16)
        preview_layout.setSpacing(12)

        preview_header = QHBoxLayout()
        preview_title = QLabel("📋 数据预览（前 10 行）")
        preview_title.setObjectName("SectionTitle")
        preview_header.addWidget(preview_title)
        preview_header.addStretch()

        self._merge_btn = QPushButton("  🔗  合并数据")
        self._merge_btn.setObjectName("PrimaryButton")
        self._merge_btn.setCursor(Qt.PointingHandCursor)
        self._merge_btn.setEnabled(False)
        self._merge_btn.clicked.connect(self._do_merge)
        preview_header.addWidget(self._merge_btn)

        preview_layout.addLayout(preview_header)

        self._preview_table = QTableWidget()
        self._preview_table.setMinimumHeight(200)
        self._preview_table.setAlternatingRowColors(True)
        self._preview_table.setEditTriggers(QTableWidget.NoEditTriggers)
        preview_layout.addWidget(self._preview_table)

        self._preview_hint = QLabel("导入两张表后，在此预览数据并执行合并")
        self._preview_hint.setStyleSheet("color: #94A3B8; font-size: 13px; padding: 16px; text-align: center;")
        self._preview_hint.setAlignment(Qt.AlignCenter)
        preview_layout.addWidget(self._preview_hint)

        layout.addWidget(preview_card)

        # 合并结果
        self._merge_result_label = QLabel("")
        self._merge_result_label.setWordWrap(True)
        self._merge_result_label.setStyleSheet("font-size: 13px; padding: 4px 0;")
        layout.addWidget(self._merge_result_label)

        # 下一步按钮
        next_row = QHBoxLayout()
        next_row.addStretch()
        self._next_btn = QPushButton("  🧹  前往数据清洗  →")
        self._next_btn.setObjectName("PrimaryButton")
        self._next_btn.setCursor(Qt.PointingHandCursor)
        self._next_btn.setEnabled(False)
        self._next_btn.clicked.connect(lambda: self.mw.navigate_to("clean") if self.mw else None)
        next_row.addWidget(self._next_btn)
        layout.addLayout(next_row)

        layout.addStretch()

    def _build_upload_card(self, title: str, hint: str, is_meta: bool) -> QFrame:
        card = QFrame()
        card.setObjectName("Card")
        layout = QVBoxLayout(card)
        layout.setContentsMargins(20, 16, 20, 16)
        layout.setSpacing(12)

        header = QHBoxLayout()
        t = QLabel(f"{'📄' if is_meta else '📝'} {title}")
        t.setObjectName("SectionTitle")
        header.addWidget(t)
        header.addStretch()
        layout.addLayout(header)

        h = QLabel(hint)
        h.setStyleSheet("color: #94A3B8; font-size: 12px;")
        h.setWordWrap(True)
        layout.addWidget(h)

        zone = DropZoneWidget(f"导入{title}")
        if is_meta:
            zone.file_dropped.connect(self._load_meta)
            self._meta_zone = zone
            self._meta_info_label = QLabel("")
            self._meta_info_label.setStyleSheet("color: #64748B; font-size: 12px;")
            layout.addWidget(zone)
            layout.addWidget(self._meta_info_label)
        else:
            zone.file_dropped.connect(self._load_text)
            self._text_zone = zone
            self._text_info_label = QLabel("")
            self._text_info_label.setStyleSheet("color: #64748B; font-size: 12px;")
            layout.addWidget(zone)
            layout.addWidget(self._text_info_label)

        return card

    def _build_import_summary(self, df: pd.DataFrame, fname: str) -> str:
        parts = [f"✅ {fname}", f"{len(df)} 行", f"{len(df.columns)} 列"]
        if not df.empty and len(df.columns) > 0:
            first_col = str(df.columns[0])
            head_vals = [str(v).strip() if pd.notna(v) else "" for v in df.iloc[:2, 0].tolist()]
            tail_vals = [str(v).strip() if pd.notna(v) else "" for v in df.iloc[-2:, 0].tolist()]
            parts.append(f"首列 {first_col}")
            parts.append(f"前2项 {head_vals}")
            parts.append(f"后2项 {tail_vals}")
        return "  |  ".join(parts)

    def _load_meta(self, path: str):
        try:
            df = load_file(path)
            self._meta_df = df
            fname = os.path.basename(path)
            self._meta_zone.set_loaded(fname, len(df), len(df.columns))
            self._meta_info_label.setText(self._build_import_summary(df, fname))
            get_state().metadata_df = df
            self._update_field_map()
            self._try_enable_merge()
            self._show_preview(df, "元数据表")
        except Exception as e:
            QMessageBox.critical(self, "导入失败", str(e))

    def _load_text(self, path: str):
        try:
            df = load_file(path)
            self._text_df = df
            fname = os.path.basename(path)
            self._text_zone.set_loaded(fname, len(df), len(df.columns))
            self._text_info_label.setText(self._build_import_summary(df, fname))
            get_state().text_df = df
            self._update_field_map()
            self._try_enable_merge()
            if self._meta_df is None:
                self._show_preview(df, "文本表")
        except Exception as e:
            QMessageBox.critical(self, "导入失败", str(e))

    def _update_field_map(self):
        parts = []
        if self._meta_df is not None:
            col_map, missing, unrec = detect_meta_columns(self._meta_df)
            get_state().meta_col_map = col_map
            parts.append(f"<b>元数据表字段识别：</b>")
            for std, orig in col_map.items():
                parts.append(f"  • {std} ← <span style='color:#2563EB'>{orig}</span>")
            if missing:
                parts.append(f"  ⚠️ 缺失字段：{', '.join(missing)}")

        if self._text_df is not None:
            col_map_t, missing_t, _ = detect_text_columns(self._text_df)
            get_state().text_col_map = col_map_t
            parts.append(f"<br><b>文本表字段识别：</b>")
            for std, orig in col_map_t.items():
                parts.append(f"  • {std} ← <span style='color:#2563EB'>{orig}</span>")
            if missing_t:
                parts.append(f"  ⚠️ 缺失字段：{', '.join(missing_t)}")

        self._field_map_label.setText("<br>".join(parts) if parts else "请先导入数据文件")

    def _show_preview(self, df: pd.DataFrame, title: str):
        preview = df.head(10)
        self._preview_table.clear()
        self._preview_table.setColumnCount(len(preview.columns))
        self._preview_table.setRowCount(len(preview))
        self._preview_table.setHorizontalHeaderLabels([str(c) for c in preview.columns])
        self._preview_hint.setVisible(False)
        self._preview_table.setVisible(True)

        for i, row in preview.iterrows():
            for j, val in enumerate(row):
                text = str(val)[:100] if pd.notna(val) else ""
                item = QTableWidgetItem(text)
                item.setFlags(item.flags() & ~Qt.ItemIsEditable)
                self._preview_table.setItem(i, j, item)

        self._preview_table.resizeColumnsToContents()

    def _try_enable_merge(self):
        self._merge_btn.setEnabled(
            self._meta_df is not None and self._text_df is not None
        )

    def _do_merge(self):
        state = get_state()
        if self._meta_df is None or self._text_df is None:
            QMessageBox.warning(self, "提示", "请先导入两张表")
            return

        meta_col_map = state.meta_col_map
        text_col_map = state.text_col_map

        if not meta_col_map.get("doc_id"):
            QMessageBox.critical(self, "错误", "元数据表中未找到文档编号字段（doc_id / 文档编号）")
            return
        if not text_col_map.get("doc_id"):
            QMessageBox.critical(self, "错误", "文本表中未找到文档编号字段（doc_id / 文档编号）")
            return

        try:
            merged, unmatched_meta, unmatched_text = merge_tables(
                self._meta_df, self._text_df, meta_col_map, text_col_map
            )
            state.merged_df = merged
            state.unmatched_meta = unmatched_meta
            state.unmatched_text = unmatched_text
            state.step_imported = True
            state.step_merged = True

            n = len(merged)
            nm = len(unmatched_meta)
            nt = len(unmatched_text)

            msg_parts = [f"✅ 合并成功！共匹配 <b>{n}</b> 篇文章"]
            if nm:
                msg_parts.append(f"⚠️ 元数据中有 {nm} 条记录未找到对应文本")
            if nt:
                msg_parts.append(f"⚠️ 文本中有 {nt} 条记录未找到对应元数据")

            self._merge_result_label.setText("  ".join(msg_parts))
            self._merge_result_label.setStyleSheet(
                "color: #16A34A; font-size: 13px; font-weight: bold; padding: 4px 0;"
                if not nm and not nt else
                "color: #D97706; font-size: 13px; padding: 4px 0;"
            )

            self._show_preview(merged, "合并数据集")
            self._next_btn.setEnabled(True)

            if self.mw:
                self.mw.update_header_status()
                self.mw.update_nav_states()

            logger.info(f"合并完成：{n} 篇文章")

        except Exception as e:
            QMessageBox.critical(self, "合并失败", str(e))
            logger.error(f"合并失败：{e}")

    def on_page_activated(self):
        pass
