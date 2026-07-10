"""导出能力的共享可用性描述。"""
from typing import Any, Dict, List


EXPORT_ITEMS = (
    ("merged_data", "merged_data.csv", "合并后的主数据集", "merged_df"),
    ("cleaned_records", "cleaned_records.csv", "清洗后的记录", "cleaned_df"),
    ("cleaned_corpus", "tokens_corpus.txt", "分词结果语料", "tokens_list"),
    ("lda_topic_word", "lda_topic_word.csv", "LDA 主题词", "lda_topics"),
    ("lda_doc_topic", "lda_doc_topic.csv", "LDA 文档主题分布", "lda_doc_topics"),
    ("lda_coherence", "lda_coherence.json", "LDA 一致性指标", "lda_coherence"),
    ("stm_topic_word", "stm_topic_word.csv", "STM 主题词", "stm_topics"),
    ("stm_doc_topic", "stm_doc_topic.csv", "STM 文档主题分布", "stm_doc_topics"),
    ("stm_prevalence", "stm_topic_prevalence.csv", "STM prevalence", "stm_prevalence"),
    ("session_config", "session_config.json", "会话配置", "session_payload"),
)


def list_export_items(state: Any) -> List[Dict[str, Any]]:
    items = []
    for key, filename, label, attribute in EXPORT_ITEMS:
        value = getattr(state, attribute, None)
        available = bool(value is not None and value != [] and value != {})
        items.append({
            "key": key,
            "filename": filename,
            "label": label,
            "available": available,
            "reason": None if available else "尚未生成对应结果",
        })
    return items
