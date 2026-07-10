"""用于 PySide 与 bridge 的共享主题对比数据服务。"""
from typing import Any, Dict, List

import pandas as pd


def _categorical_sort_key(value: Any) -> bytes:
    text = str(value)
    try:
        return text.encode("gb18030")
    except UnicodeEncodeError:
        return text.encode("utf-8", errors="ignore")


def build_topic_summary(df: pd.DataFrame, axis_field: str, topic_cols: List[str]) -> pd.DataFrame:
    """按横轴字段聚合主题均值，分类字段采用稳定的中文排序。"""
    if df is None or df.empty or axis_field not in df.columns:
        return pd.DataFrame()
    valid_topic_cols = [column for column in topic_cols if column in df.columns]
    if not valid_topic_cols:
        return pd.DataFrame()

    work = df[[axis_field] + valid_topic_cols].dropna(subset=[axis_field]).copy()
    if work.empty:
        return pd.DataFrame()
    if axis_field in ("year", "time_index"):
        work[axis_field] = pd.to_numeric(work[axis_field], errors="coerce")
        work = work.dropna(subset=[axis_field])
        if work.empty:
            return pd.DataFrame()
        grouped = work.groupby(axis_field, sort=True)[valid_topic_cols].mean().reset_index()
        grouped[axis_field] = grouped[axis_field].astype(int)
        return grouped

    work[axis_field] = work[axis_field].astype(str)
    grouped = work.groupby(axis_field, sort=False)[valid_topic_cols].mean().reset_index()
    grouped["_sort_key"] = grouped[axis_field].map(_categorical_sort_key)
    return grouped.sort_values("_sort_key", kind="mergesort").drop(columns="_sort_key").reset_index(drop=True)


def build_compare_summary(df: pd.DataFrame, axis_field: str = "source_name", topic_cols: List[str] | None = None) -> Dict[str, Any]:
    topic_cols = topic_cols or [column for column in df.columns if column.startswith("topic_")]
    summary = build_topic_summary(df, axis_field, topic_cols)
    return {
        "axisField": axis_field,
        "topicColumns": [column for column in topic_cols if column in summary.columns],
        "rows": summary.to_dict(orient="records"),
    }


def representative_articles(df: pd.DataFrame, limit_per_topic: int = 3) -> Dict[str, List[Dict[str, Any]]]:
    """按主题概率返回每个主题最具代表性的文章。"""
    if df is None or df.empty:
        return {}
    identity_cols = [
        column for column in ("doc_id", "title", "source_name", "date", "creator", "genre", "language", "text")
        if column in df.columns
    ]
    result: Dict[str, List[Dict[str, Any]]] = {}
    for topic_col in (column for column in df.columns if column.startswith("topic_")):
        columns = identity_cols + [topic_col]
        records = df[columns].sort_values(topic_col, ascending=False).head(limit_per_topic).copy()
        records[topic_col] = records[topic_col].astype(float)
        result[topic_col] = records.to_dict(orient="records")
    return result
