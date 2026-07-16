"""
应用全局状态管理
使用单例模式在各模块间共享数据
"""
from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any
import pandas as pd


@dataclass
class AppState:
    """应用全局状态单例"""

    # ── v2 单一文献表 ─────────────────────────────────
    documents_df: Optional[pd.DataFrame] = None
    document_col_map: Dict[str, str] = field(default_factory=dict)

    # v1 PySide6 回退界面的冻结状态；v2 bridge 不读取这些字段。
    metadata_df: Optional[pd.DataFrame] = None
    text_df: Optional[pd.DataFrame] = None
    merged_df: Optional[pd.DataFrame] = None
    unmatched_meta: Optional[pd.DataFrame] = None
    unmatched_text: Optional[pd.DataFrame] = None
    meta_col_map: Dict[str, str] = field(default_factory=dict)
    text_col_map: Dict[str, str] = field(default_factory=dict)

    # ── 文本清洗 ──────────────────────────────────────
    cleaned_df: Optional[pd.DataFrame] = None        # 清洗后可导出的记录表
    tokens_list: Optional[List[List[str]]] = None    # 分词结果列表（与 cleaned_df 行对应）
    stopwords_by_language: Dict[str, set] = field(default_factory=dict)
    stopwords: set = field(default_factory=set)
    stopwords_path: Optional[str] = None
    custom_dict_path: Optional[str] = None

    # ── 词频与词云（按语言隔离）──────────────────────
    frequency_results: Dict[str, Dict[str, Any]] = field(default_factory=dict)

    # ── 情感分析（按语言隔离）────────────────────────
    sentiment_results: Dict[str, Dict[str, Any]] = field(default_factory=dict)

    # ── 命名实体识别（按语言隔离）────────────────────
    ner_results: Dict[str, Dict[str, Any]] = field(default_factory=dict)

    # ── 按语言保存模型结果 ────────────────────────────
    lda_results: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    lda_model: Any = None
    lda_dictionary: Any = None
    lda_corpus: Any = None
    lda_topics: Optional[List[Dict]] = None
    lda_doc_topics: Optional[pd.DataFrame] = None
    lda_coherence: Optional[float] = None

    # ── STM 建模 ──────────────────────────────────────
    stm_results: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    stm_result: Any = None
    stm_topics: Optional[List[Dict]] = None
    stm_doc_topics: Optional[pd.DataFrame] = None
    stm_prevalence: Optional[pd.DataFrame] = None
    r_available: Optional[bool] = None               # R 环境是否可用

    # ── 会话配置 ──────────────────────────────────────
    output_dir: str = ""
    project_name: str = "未命名项目"
    session_payload: Dict[str, Any] = field(default_factory=dict)

    # ── 流程步骤状态 ──────────────────────────────────
    step_imported: bool = False
    step_merged: bool = False
    step_cleaned: bool = False
    step_frequency_done: bool = False
    step_sentiment_done: bool = False
    step_ner_done: bool = False
    step_lda_done: bool = False
    step_stm_done: bool = False
    cleaned_languages: set = field(default_factory=set)
    frequency_done_languages: set = field(default_factory=set)
    sentiment_done_languages: set = field(default_factory=set)
    ner_done_languages: set = field(default_factory=set)
    lda_done_languages: set = field(default_factory=set)
    stm_done_languages: set = field(default_factory=set)

    def reset(self):
        """重置所有状态"""
        self.__init__()

    def get_article_count(self) -> int:
        if self.documents_df is not None:
            return len(self.documents_df)
        if self.merged_df is not None:
            return len(self.merged_df)
        return 0

    def get_status_text(self) -> str:
        if self.documents_df is not None:
            return f"已导入 {self.get_article_count()} 篇文献"
        if self.merged_df is not None:
            return f"已导入 {self.get_article_count()} 篇文章（v1）"
        return "尚未导入数据"


# 全局单例
_state: Optional[AppState] = None


def get_state() -> AppState:
    global _state
    if _state is None:
        _state = AppState()
    return _state


def reset_state():
    global _state
    _state = AppState()
