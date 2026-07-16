"""共享导出能力与可用性描述。"""
import os
from typing import Any, Dict, List

import pandas as pd


EXPORT_ITEMS = (
    ("merged_data", "merged_data.csv", "合并后的主数据集", "merged_df"),
    ("cleaned_records", "cleaned_records.csv", "清洗后的记录", "cleaned_df"),
    ("cleaned_corpus", "tokens_corpus.txt", "分词结果语料", "tokens_list"),
    ("word_frequency", "word_frequency.csv", "词频明细", "frequency_results"),
    ("word_cloud", "word_cloud.png", "词云 PNG", "frequency_results"),
    ("sentiment_documents", "sentiment_documents.csv", "情感文献明细", "sentiment_results"),
    ("sentiment_summary", "sentiment_summary.csv", "情感聚合摘要", "sentiment_results"),
    ("entities", "entities.csv", "实体聚合表", "ner_results"),
    ("entity_mentions", "entity_mentions.csv", "实体出现明细", "ner_results"),
    ("lda_topic_word", "lda_topic_word.csv", "LDA 主题词", "lda_topics"),
    ("lda_doc_topic", "lda_doc_topic.csv", "LDA 文档主题分布", "lda_doc_topics"),
    ("lda_coherence", "lda_coherence.json", "LDA 一致性指标", "lda_coherence"),
    ("stm_topic_word", "stm_topic_word.csv", "STM 主题词", "stm_topics"),
    ("stm_doc_topic", "stm_doc_topic.csv", "STM 文档主题分布", "stm_doc_topics"),
    ("stm_prevalence", "stm_topic_prevalence.csv", "STM prevalence", "stm_prevalence"),
    ("session_config", "session_config.json", "会话配置", "session_payload"),
)


def _is_available(value: Any) -> bool:
    """判断导出结果是否存在，避免对 pandas 对象做含糊的真值比较。"""
    if value is None:
        return False
    if isinstance(value, (list, tuple, set, frozenset, dict)):
        return len(value) > 0

    empty = getattr(value, "empty", None)
    if empty is not None:
        return not bool(empty)
    return True


def list_export_items(state: Any) -> List[Dict[str, Any]]:
    items = []
    for key, filename, label, attribute in EXPORT_ITEMS:
        value = getattr(state, attribute, None)
        available = _is_available(value)
        items.append({
            "key": key,
            "filename": filename,
            "label": label,
            "available": available,
            "reason": None if available else "尚未生成对应结果",
        })
    return items


def write_frequency_outputs(
    language_dir: str,
    rows: List[Dict[str, Any]],
    png: bytes,
    selected: set,
) -> List[str]:
    """Write v2.1 frequency artifacts with one shared CSV/PNG contract."""
    exported: List[str] = []
    language = os.path.basename(os.path.normpath(language_dir))
    if "word_frequency" in selected:
        columns = [
            "rank", "word", "term_frequency", "document_frequency",
            "document_frequency_ratio", "token_share",
        ]
        pd.DataFrame(rows, columns=columns).to_csv(
            os.path.join(language_dir, "word_frequency.csv"), index=False, encoding="utf-8-sig"
        )
        exported.append(f"{language}/word_frequency.csv")
    if "word_cloud" in selected:
        with open(os.path.join(language_dir, "word_cloud.png"), "wb") as file:
            file.write(png)
        exported.append(f"{language}/word_cloud.png")
    return exported


def write_sentiment_outputs(
    language_dir: str,
    rows: List[Dict[str, Any]],
    aggregation: List[Dict[str, Any]],
    selected: set,
) -> List[str]:
    """Write v2.2 sentiment artifacts (per-document scores and grouped summary)."""
    exported: List[str] = []
    language = os.path.basename(os.path.normpath(language_dir))
    if "sentiment_documents" in selected:
        columns = [
            "doc_id", "sentiment", "sentiment_label", "score", "raw_score",
            "matched_words", "positive_hits", "negative_hits", "token_count",
            "positive_terms", "negative_terms",
        ]
        pd.DataFrame(rows, columns=columns).to_csv(
            os.path.join(language_dir, "sentiment_documents.csv"), index=False, encoding="utf-8-sig"
        )
        exported.append(f"{language}/sentiment_documents.csv")
    if "sentiment_summary" in selected:
        columns = ["group", "documents", "positive", "neutral", "negative", "average_score"]
        pd.DataFrame(aggregation, columns=columns).to_csv(
            os.path.join(language_dir, "sentiment_summary.csv"), index=False, encoding="utf-8-sig"
        )
        exported.append(f"{language}/sentiment_summary.csv")
    return exported


def write_ner_outputs(
    language_dir: str,
    entities: List[Dict[str, Any]],
    mentions: List[Dict[str, Any]],
    selected: set,
) -> List[str]:
    """Write v2.3 NER artifacts (aggregated entities and per-mention rows with positions)."""
    exported: List[str] = []
    language = os.path.basename(os.path.normpath(language_dir))
    if "entities" in selected:
        columns = [
            "rank", "entity", "entity_type", "entity_type_label",
            "mention_count", "document_count", "sources",
        ]
        pd.DataFrame(entities, columns=columns).to_csv(
            os.path.join(language_dir, "entities.csv"), index=False, encoding="utf-8-sig"
        )
        exported.append(f"{language}/entities.csv")
    if "entity_mentions" in selected:
        columns = [
            "doc_id", "entity", "entity_type", "entity_type_label",
            "start", "end", "source", "context",
        ]
        pd.DataFrame(mentions, columns=columns).to_csv(
            os.path.join(language_dir, "entity_mentions.csv"), index=False, encoding="utf-8-sig"
        )
        exported.append(f"{language}/entity_mentions.csv")
    return exported
