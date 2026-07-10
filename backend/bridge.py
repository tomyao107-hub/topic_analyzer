import argparse
import contextlib
import json
import math
import os
import sys
import tempfile
from typing import Any, Dict, List

import pandas as pd

from models.app_state import get_state, reset_state
from services.clean_service import CleanOptions, get_default_stopwords, tokenize_texts
from services.compare_service import build_compare_summary, representative_articles
from services.data_service import detect_meta_columns, detect_text_columns, load_file, merge_tables
from services.export_service import list_export_items
from services.lda_service import build_corpus, compute_coherence, get_doc_topics, get_topics, save_lda_results, train_lda
from services.stm_service import _analyze_stm_column, check_r_environment


SESSION_PAYLOAD_KEYS = (
    "metadataPath",
    "textPath",
    "metadataIdField",
    "textIdField",
    "options",
    "stopwords",
    "customDictPath",
    "numTopics",
    "passes",
    "iterations",
    "randomState",
    "minDocFreq",
    "maxDocFreqRatio",
    "outputDir",
    "projectName",
)


def _remember_session_payload(payload: Dict[str, Any]) -> None:
    """记录可 JSON 序列化的工作流输入，供下一个 bridge 进程重建状态。"""
    state = get_state()
    for key in SESSION_PAYLOAD_KEYS:
        if key in payload:
            state.session_payload[key] = payload[key]


def _sample_metadata() -> pd.DataFrame:
    return pd.DataFrame([
        {"doc_id": "001", "article_title": "市场与工厂", "newspaper": "申报", "pub_date": "1931-01-05", "genre": "新闻"},
        {"doc_id": "002", "article_title": "学校新制", "newspaper": "大公报", "pub_date": "1932-03-12", "genre": "教育"},
        {"doc_id": "003", "article_title": "城市交通", "newspaper": "申报", "pub_date": "1933-08-18", "genre": "评论"},
        {"doc_id": "004", "article_title": "乡村建设", "newspaper": "民国日报", "pub_date": "1934-11-02", "genre": "新闻"},
        {"doc_id": "005", "article_title": "金融改革", "newspaper": "大公报", "pub_date": "1935-06-22", "genre": "财经"},
        {"doc_id": "006", "article_title": "公共卫生", "newspaper": "申报", "pub_date": "1936-09-09", "genre": "社会"},
    ])


def _sample_text() -> pd.DataFrame:
    return pd.DataFrame([
        {"doc_id": "001", "text": "市场 贸易 工厂 工人 生产 商品 价格 市场 工厂 贸易"},
        {"doc_id": "002", "text": "学校 教育 学生 课程 教师 新制 学校 教育 课程"},
        {"doc_id": "003", "text": "城市 交通 道路 公共 汽车 市政 城市 道路 交通"},
        {"doc_id": "004", "text": "乡村 建设 农民 合作 水利 土地 乡村 建设 农民"},
        {"doc_id": "005", "text": "金融 银行 货币 改革 市场 价格 银行 金融"},
        {"doc_id": "006", "text": "公共 卫生 医院 疾病 城市 防疫 卫生 公共"},
    ])


def _number(value: Any) -> Any:
    if isinstance(value, float) and (math.isnan(value) or math.isinf(value)):
        return None
    return value


def _state_snapshot() -> Dict[str, Any]:
    state = get_state()
    return {
        "workflow": {
            "imported": state.step_imported,
            "merged": state.step_merged,
            "cleaned": state.step_cleaned,
            "ldaDone": state.step_lda_done,
            "stmDone": state.step_stm_done,
        },
        "session": {
            "projectName": state.project_name,
            "outputDir": state.output_dir,
            "payload": state.session_payload,
        },
        "summary": {
            "metadataRows": 0 if state.metadata_df is None else len(state.metadata_df),
            "textRows": 0 if state.text_df is None else len(state.text_df),
            "mergedRows": 0 if state.merged_df is None else len(state.merged_df),
            "unmatchedMetaRows": 0 if state.unmatched_meta is None else len(state.unmatched_meta),
            "unmatchedTextRows": 0 if state.unmatched_text is None else len(state.unmatched_text),
            "cleanDocuments": 0 if state.cleaned_df is None else len(state.cleaned_df),
            "totalTokens": 0 if not state.tokens_list else sum(len(tokens) for tokens in state.tokens_list),
            "uniqueWords": 0 if not state.tokens_list else len({word for tokens in state.tokens_list for word in tokens}),
            "ldaTopics": 0 if not state.lda_topics else len(state.lda_topics),
            "ldaCoherence": _number(state.lda_coherence),
            "stmTopics": 0 if not state.stm_topics else len(state.stm_topics),
            "exportFiles": 0,
        },
    }


def _load_or_sample(role: str, path: str | None) -> pd.DataFrame:
    if path:
        return load_file(path)
    return _sample_metadata() if role == "metadata" else _sample_text()


def _ensure_import(payload: Dict[str, Any], allow_sample: bool = False) -> Dict[str, Any]:
    state = get_state()
    if state.merged_df is not None:
        return {"mergedRows": len(state.merged_df)}

    metadata_path = payload.get("metadataPath") or payload.get("metadata_path")
    text_path = payload.get("textPath") or payload.get("text_path")
    if not allow_sample and (not metadata_path or not text_path):
        raise ValueError("未找到已导入的真实文件，请先完成数据导入后再运行此任务")
    meta_df = _load_or_sample("metadata", metadata_path)
    text_df = _load_or_sample("text", text_path)
    meta_col_map, meta_missing, _ = detect_meta_columns(meta_df)
    text_col_map, text_missing, _ = detect_text_columns(text_df)
    metadata_id_field = payload.get("metadataIdField") or payload.get("metadata_id_field")
    text_id_field = payload.get("textIdField") or payload.get("text_id_field")

    if metadata_id_field and metadata_id_field in meta_df.columns:
        meta_col_map["doc_id"] = metadata_id_field
        meta_missing = [field for field in meta_missing if field != "doc_id"]
    if text_id_field and text_id_field in text_df.columns:
        text_col_map["doc_id"] = text_id_field
        text_missing = [field for field in text_missing if field != "doc_id"]

    if meta_missing or text_missing:
        missing = ", ".join(meta_missing + text_missing)
        raise ValueError(f"缺少必填字段：{missing}")

    merged_df, unmatched_meta, unmatched_text = merge_tables(meta_df, text_df, meta_col_map, text_col_map)
    state.metadata_df = meta_df
    state.text_df = text_df
    state.meta_col_map = meta_col_map
    state.text_col_map = text_col_map
    state.merged_df = merged_df
    state.unmatched_meta = unmatched_meta
    state.unmatched_text = unmatched_text
    state.step_imported = True
    state.step_merged = True
    return {
        "metadataRows": len(meta_df),
        "textRows": len(text_df),
        "mergedRows": len(merged_df),
        "unmatchedMetaRows": len(unmatched_meta),
        "unmatchedTextRows": len(unmatched_text),
    }


def _clean_options(payload: Dict[str, Any]) -> CleanOptions:
    options = CleanOptions()
    values = payload.get("options") or {}
    options.remove_empty = bool(values.get("removeEmpty", True))
    options.remove_duplicates = bool(values.get("removeDuplicates", True))
    options.ocr_clean = bool(values.get("ocrClean", True))
    options.remove_punct = bool(values.get("removePunct", True))
    options.remove_numbers = bool(values.get("removeNumbers", True))
    options.traditional_to_simplified = bool(values.get("traditionalToSimplified", False))
    options.min_text_length = int(values.get("minTextLength", 2))
    options.min_token_freq = int(values.get("minTokenFreq", 1))
    options.min_doc_freq = int(values.get("minDocFreq", 1))
    options.max_doc_freq_ratio = float(values.get("maxDocFreqRatio", 0.95))
    return options


def _ensure_clean(payload: Dict[str, Any]) -> Dict[str, Any]:
    state = get_state()
    if state.tokens_list:
        return {"documents": len(state.tokens_list)}

    _ensure_import(payload)
    options = _clean_options(payload)
    stopwords = set(payload.get("stopwords") or []) or get_default_stopwords()
    texts = state.merged_df["text"].fillna("").astype(str).tolist()
    tokens_list, stats = tokenize_texts(texts, options, stopwords, payload.get("customDictPath"))
    cleaned_df = state.merged_df.copy()
    cleaned_df["tokens"] = [" ".join(tokens) for tokens in tokens_list]
    if options.remove_empty:
        keep = [len(tokens) > 0 for tokens in tokens_list]
        cleaned_df = cleaned_df[keep].reset_index(drop=True)
        tokens_list = [tokens for tokens in tokens_list if tokens]

    state.cleaned_df = cleaned_df
    state.tokens_list = tokens_list
    state.stopwords = stopwords
    state.step_cleaned = True
    return {
        "documents": len(tokens_list),
        "totalTokens": stats["total_tokens"],
        "uniqueWords": stats["unique_words"],
    }


def _run_lda(payload: Dict[str, Any]) -> Dict[str, Any]:
    state = get_state()
    _ensure_clean(payload)
    dictionary, corpus, filtered_tokens = build_corpus(
        state.tokens_list,
        min_doc_freq=int(payload.get("minDocFreq", 1)),
        max_doc_freq_ratio=float(payload.get("maxDocFreqRatio", 0.95)),
    )
    model = train_lda(
        corpus,
        dictionary,
        num_topics=int(payload.get("numTopics", 3)),
        passes=int(payload.get("passes", 2)),
        iterations=int(payload.get("iterations", 40)),
        random_state=int(payload.get("randomState", 42)),
    )
    topics = get_topics(model, n_words=8)
    coherence = compute_coherence(model, corpus, dictionary, filtered_tokens)
    doc_topics = get_doc_topics(model, corpus, state.cleaned_df, list(range(len(filtered_tokens))))
    state.lda_model = model
    state.lda_dictionary = dictionary
    state.lda_corpus = corpus
    state.lda_topics = topics
    state.lda_doc_topics = doc_topics
    state.lda_coherence = coherence
    state.step_lda_done = True
    return {"topicCount": len(topics), "coherence": _number(coherence)}


def _run_stm_check() -> Dict[str, Any]:
    with contextlib.redirect_stdout(sys.stderr):
        ok, message = check_r_environment()
    state = get_state()
    state.r_available = ok
    if ok:
        state.step_stm_done = True
        state.stm_topics = [{"topic_id": 0, "words": [], "label": "STM 环境可用"}]
    return {"available": ok, "message": message}


def _run_compare(payload: Dict[str, Any]) -> Dict[str, Any]:
    state = get_state()
    if state.lda_doc_topics is None:
        _run_lda(payload)
    doc_topics = state.lda_doc_topics
    rows = 0 if doc_topics is None else len(doc_topics)
    groups = [] if doc_topics is None or "newspaper" not in doc_topics else sorted(doc_topics["newspaper"].dropna().astype(str).unique().tolist())
    return {"rows": rows, "groups": groups, "representativeArticles": min(rows, 3)}


def _run_export(payload: Dict[str, Any]) -> Dict[str, Any]:
    state = get_state()
    if state.lda_topics is None:
        _run_lda(payload)

    output_dir = payload.get("outputDir") or os.path.join(tempfile.gettempdir(), "topic-analyzer-output")
    project_name = payload.get("projectName") or state.project_name
    os.makedirs(output_dir, exist_ok=True)
    state.output_dir = output_dir
    state.project_name = project_name
    exported: List[str] = []

    if state.merged_df is not None:
        state.merged_df.to_csv(os.path.join(output_dir, "merged_data.csv"), index=False, encoding="utf-8-sig")
        exported.append("merged_data.csv")
    if state.cleaned_df is not None:
        state.cleaned_df.to_csv(os.path.join(output_dir, "cleaned_records.csv"), index=False, encoding="utf-8-sig")
        exported.append("cleaned_records.csv")
    if state.tokens_list:
        with open(os.path.join(output_dir, "tokens_corpus.txt"), "w", encoding="utf-8") as f:
            for tokens in state.tokens_list:
                f.write(" ".join(tokens) + "\n")
        exported.append("tokens_corpus.txt")
    if state.lda_topics and state.lda_doc_topics is not None:
        save_lda_results(state.lda_topics, state.lda_doc_topics, state.lda_coherence or 0, output_dir)
        exported.extend(["lda_topic_word.csv", "lda_doc_topic.csv", "lda_coherence.json"])
    with open(os.path.join(output_dir, "session_config.json"), "w", encoding="utf-8") as f:
        json.dump(state.session_payload, f, ensure_ascii=False, indent=2)
    exported.append("session_config.json")
    return {"outputDir": output_dir, "exported": exported, "count": len(exported)}


def _json_records(df: pd.DataFrame) -> List[Dict[str, Any]]:
    """通过 pandas JSON 编码统一处理日期、NaN 与 numpy 标量。"""
    if df is None or df.empty:
        return []
    return json.loads(df.to_json(orient="records", date_format="iso", force_ascii=False))


def _preview_dataframe(name: str, df: pd.DataFrame, payload: Dict[str, Any]) -> Dict[str, Any]:
    page = max(1, int(payload.get("page", 1)))
    page_size = min(500, max(1, int(payload.get("pageSize", payload.get("limit", 50)))))
    total = 0 if df is None else len(df)
    start = (page - 1) * page_size
    rows = pd.DataFrame() if df is None else df.iloc[start:start + page_size]
    return {
        "table": name,
        "columns": [] if df is None else [str(column) for column in df.columns],
        "rows": _json_records(rows),
        "page": page,
        "pageSize": page_size,
        "total": total,
        "hasMore": start + page_size < total,
    }


def _table_preview(payload: Dict[str, Any]) -> Dict[str, Any]:
    table = str(payload.get("table") or payload.get("source") or "merged")
    state = get_state()
    if table in {"metadata", "text", "merged"}:
        _ensure_import(payload)
    elif table == "cleaned":
        _ensure_clean(payload)
    elif table == "ldaDocTopics":
        _run_lda(payload)
    elif table == "stmDocTopics":
        _ensure_clean(payload)
        if state.stm_doc_topics is None:
            raise ValueError("尚未完成 STM 训练，无法预览 STM 文档主题分布")
    else:
        raise ValueError(f"不支持的表格预览来源：{table}")
    frames = {
        "metadata": state.metadata_df,
        "text": state.text_df,
        "merged": state.merged_df,
        "cleaned": state.cleaned_df,
        "ldaDocTopics": state.lda_doc_topics,
        "stmDocTopics": state.stm_doc_topics,
    }
    return _preview_dataframe(table, frames[table], payload)


def _clean_preview(payload: Dict[str, Any]) -> Dict[str, Any]:
    _ensure_clean(payload)
    state = get_state()
    preview = _preview_dataframe("cleaned", state.cleaned_df, payload)
    preview["documents"] = len(state.tokens_list or [])
    preview["tokenColumn"] = "tokens"
    return preview


def _lda_result(payload: Dict[str, Any]) -> Dict[str, Any]:
    _run_lda(payload)
    state = get_state()
    return {
        "topics": state.lda_topics or [],
        "coherence": _number(state.lda_coherence),
        "documentTopics": _preview_dataframe("ldaDocTopics", state.lda_doc_topics, payload),
    }


def _stm_covariates(payload: Dict[str, Any]) -> Dict[str, Any]:
    _ensure_clean(payload)
    state = get_state()
    df = state.cleaned_df if state.cleaned_df is not None else state.merged_df
    items = []
    for column in df.columns:
        ok, reason = _analyze_stm_column(df, column)
        items.append({"field": str(column), "available": ok, "reason": reason})
    return {"covariates": items}


def _compare_summary(payload: Dict[str, Any]) -> Dict[str, Any]:
    _run_lda(payload)
    state = get_state()
    axis_field = str(payload.get("axisField") or "newspaper")
    summary = build_compare_summary(state.lda_doc_topics, axis_field)
    summary["representativeArticles"] = representative_articles(
        state.lda_doc_topics, int(payload.get("representativeLimit", 3))
    )
    return summary


def _export_items(payload: Dict[str, Any]) -> Dict[str, Any]:
    _ensure_import(payload)
    if "options" in payload:
        _ensure_clean(payload)
    if "numTopics" in payload:
        _run_lda(payload)
    return {"items": list_export_items(get_state())}


def handle(command: str, payload: Dict[str, Any]) -> Dict[str, Any]:
    # Tauri 每次任务都会创建新的 Python 进程。新的导入才应清空旧工作流；
    # 其他任务依赖其传入的 session payload 重建真实文件对应的状态。
    if command in {"task.import", "import.merge", "import.load_table"}:
        reset_state()
    _remember_session_payload(payload)
    if command in {"session.get_state", "task.import"}:
        data = _ensure_import(payload, allow_sample=True) if command == "task.import" else {}
    elif command in {"import.merge", "import.load_table"}:
        data = _ensure_import(payload, allow_sample=True)
    elif command in {"task.clean", "clean.run"}:
        data = _ensure_clean(payload)
    elif command in {"task.lda", "lda.train"}:
        data = _run_lda(payload)
    elif command in {"task.stm", "stm.check_r", "stm.train"}:
        data = _run_stm_check()
    elif command == "table.preview":
        data = _table_preview(payload)
    elif command == "clean.preview":
        data = _clean_preview(payload)
    elif command == "lda.get_result":
        data = _lda_result(payload)
    elif command == "stm.analyze_covariates":
        data = _stm_covariates(payload)
    elif command in {"task.compare", "compare.build_summary"}:
        data = _compare_summary(payload)
    elif command == "export.list_items":
        data = _export_items(payload)
    elif command in {"task.export", "export.run"}:
        data = _run_export(payload)
    else:
        raise ValueError(f"未知命令：{command}")

    snapshot = _state_snapshot()
    if command in {"task.export", "export.run"}:
        snapshot["summary"]["exportFiles"] = data.get("count", 0)
    return {"ok": True, "data": data, "state": snapshot}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("command")
    parser.add_argument("payload", nargs="?", default="{}")
    args = parser.parse_args()

    try:
        payload = json.loads(args.payload)
        result = handle(args.command, payload)
    except Exception as exc:
        result = {
            "ok": False,
            "error": {
                "code": exc.__class__.__name__.upper(),
                "message": str(exc),
                "recoverable": True,
                "suggestion": "请检查输入文件、Python 依赖和外部运行环境。",
            },
            "state": _state_snapshot(),
        }

    sys.stdout.write(json.dumps(result, ensure_ascii=False))
    return 0 if result.get("ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())
