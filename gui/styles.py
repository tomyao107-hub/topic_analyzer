"""
全局 QSS 样式表
现代极简浅色主题，专业学术风格
"""

APP_STYLE = """
/* ═══════════════════════════════════════════════════
   全局基础
═══════════════════════════════════════════════════ */
QMainWindow, QWidget {
    background-color: #F0F4F8;
    color: #1E293B;
    font-family: "Microsoft YaHei", "PingFang SC", "Noto Sans CJK SC", "SimHei", Arial, sans-serif;
    font-size: 13px;
}

QScrollArea {
    border: none;
    background-color: transparent;
}
QScrollArea > QWidget > QWidget {
    background-color: transparent;
}

/* ═══════════════════════════════════════════════════
   左侧导航栏
═══════════════════════════════════════════════════ */
#NavBar {
    background-color: #1E293B;
    min-width: 200px;
    max-width: 200px;
    border-right: 1px solid #334155;
}

#NavTitle {
    color: #F8FAFC;
    font-size: 14px;
    font-weight: bold;
    padding: 20px 16px 4px 16px;
}

#NavSubtitle {
    color: #64748B;
    font-size: 11px;
    padding: 0px 16px 16px 16px;
}

#NavSeparator {
    background-color: #334155;
    max-height: 1px;
    margin: 4px 16px;
}

QPushButton#NavButton {
    background-color: transparent;
    color: #94A3B8;
    border: none;
    border-radius: 8px;
    padding: 10px 14px;
    text-align: left;
    font-size: 13px;
    margin: 2px 8px;
}
QPushButton#NavButton:hover {
    background-color: #334155;
    color: #CBD5E1;
}
QPushButton#NavButton[active="true"] {
    background-color: #2563EB;
    color: #FFFFFF;
    font-weight: bold;
}

/* ═══════════════════════════════════════════════════
   顶部工具栏
═══════════════════════════════════════════════════ */
#TopBar {
    background-color: #FFFFFF;
    border-bottom: 1px solid #E2E8F0;
    min-height: 56px;
    max-height: 56px;
}

#AppTitle {
    color: #1E293B;
    font-size: 16px;
    font-weight: bold;
}

#ProjectLabel {
    color: #64748B;
    font-size: 12px;
}

#StatusChip {
    background-color: #EFF6FF;
    color: #2563EB;
    border-radius: 12px;
    padding: 4px 12px;
    font-size: 12px;
    font-weight: bold;
}

/* ═══════════════════════════════════════════════════
   底部状态栏
═══════════════════════════════════════════════════ */
#BottomBar {
    background-color: #FFFFFF;
    border-top: 1px solid #E2E8F0;
    min-height: 32px;
    max-height: 32px;
}

#StatusLabel {
    color: #475569;
    font-size: 12px;
    padding: 0 12px;
}

QProgressBar {
    border: none;
    background-color: #E2E8F0;
    border-radius: 3px;
    height: 4px;
    max-height: 4px;
    text-align: center;
}
QProgressBar::chunk {
    background-color: #2563EB;
    border-radius: 3px;
}

/* ═══════════════════════════════════════════════════
   卡片容器
═══════════════════════════════════════════════════ */
QFrame#Card {
    background-color: #FFFFFF;
    border: 1px solid #E2E8F0;
    border-radius: 10px;
}

QFrame#CardSection {
    background-color: #F8FAFC;
    border: 1px solid #E2E8F0;
    border-radius: 8px;
}

/* ═══════════════════════════════════════════════════
   页面标题
═══════════════════════════════════════════════════ */
QLabel#PageTitle {
    color: #0F172A;
    font-size: 22px;
    font-weight: bold;
}

QLabel#PageSubtitle {
    color: #64748B;
    font-size: 13px;
}

QLabel#SectionTitle {
    color: #1E293B;
    font-size: 14px;
    font-weight: bold;
}

QLabel#FieldLabel {
    color: #475569;
    font-size: 12px;
}

/* ═══════════════════════════════════════════════════
   按钮
═══════════════════════════════════════════════════ */
/* 主按钮 */
QPushButton#PrimaryButton {
    background-color: #2563EB;
    color: #FFFFFF;
    border: none;
    border-radius: 8px;
    padding: 10px 20px;
    font-size: 13px;
    font-weight: bold;
    min-height: 36px;
}
QPushButton#PrimaryButton:hover {
    background-color: #1D4ED8;
}
QPushButton#PrimaryButton:pressed {
    background-color: #1E40AF;
}
QPushButton#PrimaryButton:disabled {
    background-color: #BFDBFE;
    color: #93C5FD;
}

/* 次要按钮 */
QPushButton#SecondaryButton {
    background-color: #F1F5F9;
    color: #475569;
    border: 1px solid #E2E8F0;
    border-radius: 8px;
    padding: 8px 18px;
    font-size: 13px;
    min-height: 36px;
}
QPushButton#SecondaryButton:hover {
    background-color: #E2E8F0;
    color: #1E293B;
}
QPushButton#SecondaryButton:disabled {
    color: #94A3B8;
}

/* 文本按钮 */
QPushButton#TextButton {
    background-color: transparent;
    color: #2563EB;
    border: none;
    padding: 4px 8px;
    font-size: 12px;
}
QPushButton#TextButton:hover {
    color: #1D4ED8;
    text-decoration: underline;
}

/* 危险按钮 */
QPushButton#DangerButton {
    background-color: #FEF2F2;
    color: #DC2626;
    border: 1px solid #FECACA;
    border-radius: 8px;
    padding: 8px 16px;
    font-size: 13px;
}
QPushButton#DangerButton:hover {
    background-color: #FEE2E2;
}

/* ═══════════════════════════════════════════════════
   输入控件
═══════════════════════════════════════════════════ */
QLineEdit, QTextEdit, QPlainTextEdit {
    background-color: #FFFFFF;
    border: 1px solid #CBD5E1;
    border-radius: 6px;
    padding: 6px 10px;
    color: #1E293B;
    selection-background-color: #BFDBFE;
}
QLineEdit:focus, QTextEdit:focus, QPlainTextEdit:focus {
    border: 1px solid #3B82F6;
    outline: none;
}

QSpinBox, QDoubleSpinBox {
    background-color: #FFFFFF;
    border: 1px solid #CBD5E1;
    border-radius: 6px;
    padding: 5px 8px;
    color: #1E293B;
    min-height: 30px;
}
QSpinBox:focus, QDoubleSpinBox:focus {
    border-color: #3B82F6;
}
QSpinBox::up-button, QSpinBox::down-button,
QDoubleSpinBox::up-button, QDoubleSpinBox::down-button {
    background-color: #F1F5F9;
    border: none;
    border-radius: 3px;
    width: 18px;
}

QComboBox {
    background-color: #FFFFFF;
    border: 1px solid #CBD5E1;
    border-radius: 6px;
    padding: 6px 10px;
    color: #1E293B;
    min-height: 32px;
}
QComboBox:focus {
    border-color: #3B82F6;
}
QComboBox::drop-down {
    border: none;
    width: 24px;
}
QComboBox QAbstractItemView {
    background-color: #FFFFFF;
    border: 1px solid #E2E8F0;
    border-radius: 6px;
    selection-background-color: #EFF6FF;
    selection-color: #1E293B;
}

QCheckBox {
    color: #475569;
    font-size: 13px;
    spacing: 8px;
}
QCheckBox::indicator {
    width: 16px;
    height: 16px;
    border: 1px solid #CBD5E1;
    border-radius: 4px;
    background-color: #FFFFFF;
}
QCheckBox::indicator:checked {
    background-color: #2563EB;
    border-color: #2563EB;
    image: url(none);
}
QCheckBox::indicator:hover {
    border-color: #3B82F6;
}

/* ═══════════════════════════════════════════════════
   表格
═══════════════════════════════════════════════════ */
QTableWidget, QTableView {
    background-color: #FFFFFF;
    border: 1px solid #E2E8F0;
    border-radius: 8px;
    gridline-color: #F1F5F9;
    selection-background-color: #EFF6FF;
    selection-color: #1E293B;
    alternate-background-color: #F8FAFC;
}
QTableWidget::item, QTableView::item {
    padding: 6px 10px;
    border: none;
}
QHeaderView::section {
    background-color: #F1F5F9;
    color: #475569;
    font-weight: bold;
    font-size: 12px;
    padding: 8px 10px;
    border: none;
    border-bottom: 1px solid #E2E8F0;
    border-right: 1px solid #E2E8F0;
}
QHeaderView::section:last {
    border-right: none;
}

/* ═══════════════════════════════════════════════════
   分组框
═══════════════════════════════════════════════════ */
QGroupBox {
    border: 1px solid #E2E8F0;
    border-radius: 8px;
    margin-top: 14px;
    padding: 8px;
    font-size: 13px;
    color: #475569;
}
QGroupBox::title {
    subcontrol-origin: margin;
    subcontrol-position: top left;
    left: 12px;
    top: 2px;
    background-color: #F0F4F8;
    padding: 0 6px;
}

/* ═══════════════════════════════════════════════════
   滚动条
═══════════════════════════════════════════════════ */
QScrollBar:vertical {
    background-color: transparent;
    width: 8px;
    border-radius: 4px;
}
QScrollBar::handle:vertical {
    background-color: #CBD5E1;
    border-radius: 4px;
    min-height: 30px;
}
QScrollBar::handle:vertical:hover {
    background-color: #94A3B8;
}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
    height: 0px;
}

QScrollBar:horizontal {
    background-color: transparent;
    height: 8px;
    border-radius: 4px;
}
QScrollBar::handle:horizontal {
    background-color: #CBD5E1;
    border-radius: 4px;
    min-width: 30px;
}

/* ═══════════════════════════════════════════════════
   标签页
═══════════════════════════════════════════════════ */
QTabWidget::pane {
    border: 1px solid #E2E8F0;
    border-radius: 8px;
    background-color: #FFFFFF;
    top: -1px;
}
QTabBar::tab {
    background-color: #F1F5F9;
    color: #64748B;
    border: 1px solid #E2E8F0;
    border-bottom: none;
    border-radius: 6px 6px 0 0;
    padding: 8px 16px;
    margin-right: 2px;
}
QTabBar::tab:selected {
    background-color: #FFFFFF;
    color: #1E293B;
    font-weight: bold;
}
QTabBar::tab:hover {
    background-color: #E2E8F0;
}

/* ═══════════════════════════════════════════════════
   消息框和工具提示
═══════════════════════════════════════════════════ */
QToolTip {
    background-color: #1E293B;
    color: #F8FAFC;
    border: none;
    border-radius: 6px;
    padding: 6px 10px;
    font-size: 12px;
}

QMessageBox {
    background-color: #FFFFFF;
}
QMessageBox QPushButton {
    min-width: 80px;
    padding: 6px 16px;
    border-radius: 6px;
    background-color: #2563EB;
    color: white;
    border: none;
}

/* ═══════════════════════════════════════════════════
   Splitter
═══════════════════════════════════════════════════ */
QSplitter::handle {
    background-color: #E2E8F0;
}
QSplitter::handle:hover {
    background-color: #CBD5E1;
}

/* ═══════════════════════════════════════════════════
   信息提示标签
═══════════════════════════════════════════════════ */
QLabel#InfoBadge {
    background-color: #EFF6FF;
    color: #2563EB;
    border-radius: 10px;
    padding: 3px 10px;
    font-size: 11px;
    font-weight: bold;
}

QLabel#SuccessBadge {
    background-color: #F0FDF4;
    color: #16A34A;
    border-radius: 10px;
    padding: 3px 10px;
    font-size: 11px;
    font-weight: bold;
}

QLabel#WarningBadge {
    background-color: #FFFBEB;
    color: #D97706;
    border-radius: 10px;
    padding: 3px 10px;
    font-size: 11px;
    font-weight: bold;
}

QLabel#ErrorBadge {
    background-color: #FEF2F2;
    color: #DC2626;
    border-radius: 10px;
    padding: 3px 10px;
    font-size: 11px;
    font-weight: bold;
}

/* ═══════════════════════════════════════════════════
   拖放上传区域
═══════════════════════════════════════════════════ */
QFrame#DropZone {
    background-color: #F8FAFC;
    border: 2px dashed #CBD5E1;
    border-radius: 10px;
}
QFrame#DropZone:hover {
    border-color: #3B82F6;
    background-color: #EFF6FF;
}
QFrame#DropZoneActive {
    background-color: #EFF6FF;
    border: 2px dashed #3B82F6;
    border-radius: 10px;
}
"""
