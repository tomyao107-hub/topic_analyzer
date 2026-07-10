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

    # ── 数据导入 ──────────────────────────────────────
    metadata_df: Optional[pd.DataFrame] = None       # 元数据表（原始）
    text_df: Optional[pd.DataFrame] = None           # 文本表（原始）
    merged_df: Optional[pd.DataFrame] = None         # 合并后主数据集
    unmatched_meta: Optional[pd.DataFrame] = None    # 未匹配的元数据记录
    unmatched_text: Optional[pd.DataFrame] = None    # 未匹配的文本记录
    meta_col_map: Dict[str, str] = field(default_factory=dict)   # 字段映射
    text_col_map: Dict[str, str] = field(default_factory=dict)

    # ── 文本清洗 ──────────────────────────────────────
    cleaned_df: Optional[pd.DataFrame] = None        # 清洗后可导出的记录表
    tokens_list: Optional[List[List[str]]] = None    # 分词结果列表（与 cleaned_df 行对应）
    stopwords: set = field(default_factory=set)       # 停用词集合
    stopwords_path: Optional[str] = None             # 外部停用词文件路径
    custom_dict_path: Optional[str] = None

    # ── LDA 建模 ──────────────────────────────────────
    lda_model: Any = None                             # gensim LDA 模型
    lda_dictionary: Any = None                        # gensim Dictionary
    lda_corpus: Any = None                            # BoW 语料
    lda_topics: Optional[List[Dict]] = None           # 每个主题的关键词
    lda_doc_topics: Optional[pd.DataFrame] = None     # 文档-主题分布
    lda_coherence: Optional[float] = None

    # ── STM 建模 ──────────────────────────────────────
    stm_result: Any = None                            # rpy2 STM 结果对象
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
    step_lda_done: bool = False
    step_stm_done: bool = False

    def reset(self):
        """重置所有状态"""
        self.__init__()

    def get_article_count(self) -> int:
        if self.merged_df is not None:
            return len(self.merged_df)
        return 0

    def get_status_text(self) -> str:
        if self.merged_df is not None:
            return f"已导入 {self.get_article_count()} 篇文章"
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
