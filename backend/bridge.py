"""Tauri 与 Python 分析能力之间的 v2 单表/双语 JSON 桥。"""
import argparse
import base64
import contextlib
import json
import math
import os
import sys
from collections import Counter
from datetime import datetime
from typing import Any, Dict, List

import pandas as pd

from models.app_state import get_state, reset_state
from services.clean_service import CleanOptions, clean_text, get_default_stopwords, tokenize_documents
from services.compare_service import build_compare_summary, representative_articles
from services.data_service import DocumentValidationError, load_documents
from services.frequency_service import FrequencyOptions, analyze_word_frequency, render_word_cloud_png
from services.export_service import write_frequency_outputs
from services.lda_service import build_corpus, compute_coherence, get_doc_topics, get_topics, open_pyldavis, train_lda
from services.stm_service import _analyze_stm_column, check_r_environment, train_stm

LANGUAGES = ("zh", "en")
LANGUAGE_LABELS = {"zh": "中文", "en": "英文"}


def _remember_session_payload(payload: Dict[str, Any]) -> None:
    state = get_state()
    state.session_payload.update(payload)
    state.project_name = str(payload.get("projectName") or state.project_name)
    state.output_dir = str(payload.get("outputDir") or state.output_dir)


def _number(value: Any) -> Any:
    if isinstance(value, float) and (math.isnan(value) or math.isinf(value)):
        return None
    return value


def _json_safe(value: Any) -> Any:
    """递归清洗，保证结果可被严格 JSON（Rust serde_json）解析。

    处理：NaN/Inf → None、numpy 标量 → 原生类型、pandas 缺失值 → None。
    Rust 端使用严格 JSON，裸 NaN/Infinity 会导致整个响应解析失败，
    因此在写出前统一在这里兜底。
    """
    if value is None:
        return None
    if isinstance(value, float):
        return None if (math.isnan(value) or math.isinf(value)) else value
    if isinstance(value, (str, bool, int)):
        return value
    if isinstance(value, dict):
        return {str(key): _json_safe(item) for key, item in value.items()}
    if isinstance(value, (list, tuple, set, frozenset)):
        return [_json_safe(item) for item in value]
    # numpy 标量、pandas 缺失值等
    try:
        import numpy as _np
        if isinstance(value, _np.generic):
            scalar = value.item()
            return _json_safe(scalar)
    except Exception:
        pass
    try:
        if pd.isna(value):
            return None
    except (TypeError, ValueError):
        pass
    return value


def _json_records(df: pd.DataFrame) -> List[Dict[str, Any]]:
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


def _language_counts(df: pd.DataFrame | None) -> Dict[str, int]:
    if df is None or "language" not in df.columns:
        return {language: 0 for language in LANGUAGES}
    values = df["language"].value_counts()
    return {language: int(values.get(language, 0)) for language in LANGUAGES}


def _state_snapshot() -> Dict[str, Any]:
    state = get_state()
    lda_topics = {
        language: len(state.lda_results.get(language, {}).get("topics") or [])
        for language in LANGUAGES
    }
    lda_coherence = {
        language: _number(state.lda_results.get(language, {}).get("coherence"))
        for language in LANGUAGES
    }
    stm_topics = {
        language: len(state.stm_results.get(language, {}).get("topics") or [])
        for language in LANGUAGES
    }
    token_counts = {language: 0 for language in LANGUAGES}
    unique_words = {language: set() for language in LANGUAGES}
    if state.cleaned_df is not None and state.tokens_list is not None:
        for language, tokens in zip(state.cleaned_df["language"].tolist(), state.tokens_list):
            token_counts[language] += len(tokens)
            unique_words[language].update(tokens)
    return {
        "workflow": {
            "imported": state.step_imported,
            "cleaned": state.step_cleaned,
            "frequencyDone": bool(state.frequency_done_languages),
            "ldaDone": bool(state.lda_done_languages),
            "stmDone": bool(state.stm_done_languages),
        },
        "languageWorkflow": {
            language: {
                "cleaned": language in state.cleaned_languages,
                "frequencyDone": language in state.frequency_done_languages,
                "ldaDone": language in state.lda_done_languages,
                "stmDone": language in state.stm_done_languages,
            }
            for language in LANGUAGES
        },
        "session": {
            "schemaVersion": 2,
            "projectName": state.project_name,
            "outputDir": state.output_dir,
            "payload": state.session_payload,
        },
        "summary": {
            "documentRows": 0 if state.documents_df is None else len(state.documents_df),
            "languageRows": _language_counts(state.documents_df),
            "cleanDocuments": 0 if state.cleaned_df is None else len(state.cleaned_df),
            "totalTokens": token_counts,
            "uniqueWords": {key: len(value) for key, value in unique_words.items()},
            "frequencyWords": {
                language: len(state.frequency_results.get(language, {}).get("rows") or [])
                for language in LANGUAGES
            },
            "ldaTopics": lda_topics,
            "ldaCoherence": lda_coherence,
            "stmTopics": stm_topics,
            "exportFiles": 0,
        },
    }


def _ensure_import(payload: Dict[str, Any]) -> Dict[str, Any]:
    state = get_state()
    if state.documents_df is not None:
        return _import_result()
    data_path = str(payload.get("dataPath") or payload.get("data_path") or "").strip()
    if not data_path:
        raise ValueError("未找到 v2 文献表，请先选择包含 doc_id、text、language 的 CSV/Excel 文件")
    mapping = payload.get("fieldMapping") or payload.get("field_mapping") or {}
    documents, detected, unrecognized = load_documents(data_path, mapping)
    state.documents_df = documents
    state.document_col_map = detected
    state.step_imported = True
    state.session_payload["unrecognizedColumns"] = unrecognized
    return _import_result()


def _unique_strings(df: pd.DataFrame, column: str) -> List[str]:
    if df is None or column not in df.columns:
        return []
    return sorted({str(value).strip() for value in df[column].dropna() if str(value).strip()})


def _covariate_items(df: pd.DataFrame) -> List[Dict[str, Any]]:
    excluded = {"doc_id", "text", "language", "tokens", "cleaned_text", "token_count"}
    items = []
    if df is None:
        return items
    for column in df.columns:
        if str(column) in excluded:
            continue
        ok, reason = _analyze_stm_column(df, column)
        items.append({"field": str(column), "available": ok, "reason": reason})
    return items


def _metadata_fields(df: pd.DataFrame) -> List[Dict[str, Any]]:
    excluded = {"doc_id", "text", "language", "tokens", "cleaned_text", "token_count"}
    fields = []
    for column in df.columns:
        if column in excluded:
            continue
        values = _unique_strings(df, column)
        fields.append({"field": str(column), "values": values[:200], "uniqueCount": len(values)})
    return fields


def _import_result() -> Dict[str, Any]:
    state = get_state()
    documents = state.documents_df
    return {
        "documentRows": len(documents),
        "languageRows": _language_counts(documents),
        "columns": [str(column) for column in documents.columns],
        "mapping": dict(state.document_col_map),
        "unrecognizedColumns": list(state.session_payload.get("unrecognizedColumns") or []),
        "preview": _preview_dataframe("documents", documents, {"page": 1, "pageSize": 10}),
        "metadataFields": _metadata_fields(documents),
        "covariates": _covariate_items(documents),
    }


def _clean_values(payload: Dict[str, Any]) -> Dict[str, Any]:
    return payload.get("cleanConfig") or payload.get("options") or payload


def _clean_options(payload: Dict[str, Any]) -> CleanOptions:
    values = _clean_values(payload)
    zh_values = values.get("zh") or {}
    en_values = values.get("en") or {}
    options = CleanOptions()
    options.remove_empty = bool(values.get("removeEmpty", True))
    options.remove_duplicates = bool(values.get("removeDuplicates", True))
    options.ocr_clean = bool(values.get("ocrClean", True))
    options.remove_punct = bool(values.get("removePunct", True))
    options.remove_numbers = bool(values.get("removeNumbers", True))
    options.min_text_length = int(values.get("minTextLength", 10))
    options.min_token_freq = int(values.get("minTokenFreq", 1))
    options.min_doc_freq = int(values.get("minDocFreq", 2))
    options.max_doc_freq_ratio = float(values.get("maxDocFreqRatio", 0.95))
    options.traditional_to_simplified = bool(zh_values.get("traditionalToSimplified", False))
    options.zh_min_token_length = int(zh_values.get("minTokenLength", 1))
    options.lowercase_english = bool(en_values.get("lowercase", True))
    options.repair_english_hyphenation = bool(en_values.get("repairHyphenation", True))
    options.en_min_token_length = int(en_values.get("minTokenLength", 2))
    return options


def _stopwords(payload: Dict[str, Any]) -> Dict[str, set]:
    values = _clean_values(payload)
    result = {}
    for language in LANGUAGES:
        language_values = values.get(language) or {}
        words = {str(word).strip() for word in language_values.get("stopwords", []) if str(word).strip()}
        if bool(language_values.get("useDefaultStopwords", True)):
            words |= get_default_stopwords(language)
        if language == "en":
            words = {word.casefold() for word in words}
        result[language] = words
    return result


def _ensure_clean(payload: Dict[str, Any]) -> Dict[str, Any]:
    state = get_state()
    if state.cleaned_df is not None and state.tokens_list is not None:
        return _clean_result()
    _ensure_import(payload)
    options = _clean_options(payload)
    values = _clean_values(payload)
    work_df = state.documents_df.copy()
    removed_duplicates: List[str] = []
    if options.remove_duplicates:
        duplicate = work_df.duplicated(subset=["language", "text"], keep="first")
        removed_duplicates = work_df.loc[duplicate, "doc_id"].astype(str).tolist()
        work_df = work_df.loc[~duplicate].reset_index(drop=True)
    texts = work_df["text"].astype(str).tolist()
    languages = work_df["language"].astype(str).tolist()
    stopwords = _stopwords(payload)
    tokens_list, stats = tokenize_documents(
        texts,
        languages,
        options,
        stopwords,
        (values.get("zh") or {}).get("customDictPath") or None,
    )
    if options.min_token_freq > 1:
        frequencies = {
            language: Counter(
                word for row_language, tokens in zip(languages, tokens_list)
                if row_language == language for word in tokens
            )
            for language in LANGUAGES
        }
        tokens_list = [
            [word for word in tokens if frequencies[language][word] >= options.min_token_freq]
            for language, tokens in zip(languages, tokens_list)
        ]
    cleaned = work_df.copy()
    cleaned["cleaned_text"] = [clean_text(text, options, language) for text, language in zip(texts, languages)]
    cleaned["tokens"] = [" ".join(tokens) for tokens in tokens_list]
    cleaned["token_count"] = [len(tokens) for tokens in tokens_list]
    removed_empty: List[str] = []
    if options.remove_empty:
        keep = [bool(tokens) for tokens in tokens_list]
        removed_empty = cleaned.loc[[not value for value in keep], "doc_id"].astype(str).tolist()
        cleaned = cleaned.loc[keep].reset_index(drop=True)
        tokens_list = [tokens for tokens in tokens_list if tokens]

    state.cleaned_df = cleaned
    state.tokens_list = tokens_list
    state.stopwords_by_language = stopwords
    state.cleaned_languages = set(cleaned["language"].unique().tolist())
    state.step_cleaned = True
    state.session_payload["cleaningReport"] = {
        "removedDuplicateDocIds": removed_duplicates,
        "removedEmptyDocIds": removed_empty,
    }
    return _clean_result(stats)


def _clean_result(stats: Dict[str, Any] | None = None) -> Dict[str, Any]:
    state = get_state()
    language_stats = {}
    for language in LANGUAGES:
        if state.cleaned_df is None:
            rows, tokens = 0, []
        else:
            indices = [i for i, value in enumerate(state.cleaned_df["language"].tolist()) if value == language]
            rows = len(indices)
            tokens = [state.tokens_list[i] for i in indices]
        language_stats[language] = {
            "documents": rows,
            "totalTokens": sum(len(row) for row in tokens),
            "uniqueWords": len({word for row in tokens for word in row}),
            "stopwordCount": len(state.stopwords_by_language.get(language, set())),
        }
    return {
        "documents": 0 if state.cleaned_df is None else len(state.cleaned_df),
        "totalDocuments": 0 if state.documents_df is None else len(state.documents_df),
        "languages": language_stats,
        "report": state.session_payload.get("cleaningReport") or {},
        "preview": _preview_dataframe("cleaned", state.cleaned_df, {"page": 1, "pageSize": 300}),
    }


def _frequency_options(payload: Dict[str, Any], language: str) -> FrequencyOptions:
    configs = payload.get("frequencyConfigs") or {}
    values = configs.get(language) or payload.get("frequencyConfig") or payload
    return FrequencyOptions(
        language=language,
        sort_by=str(values.get("sortBy") or "term_frequency"),
        top_n=int(values.get("topN", 50)),
        min_term_frequency=int(values.get("minTermFrequency", 1)),
        min_document_frequency=int(values.get("minDocumentFrequency", 1)),
        random_state=int(values.get("randomState", 42)),
    )


def _run_frequency(payload: Dict[str, Any], include_image: bool = True) -> Dict[str, Any]:
    state = get_state()
    _ensure_clean(payload)
    language = _selected_language(payload)
    options = _frequency_options(payload, language)
    indices = [
        index for index, value in enumerate(state.cleaned_df["language"].tolist())
        if value == language
    ]
    tokens = [state.tokens_list[index] for index in indices]
    result = analyze_word_frequency(tokens, options)
    # 词云渲染可能因缺少中文字体等原因失败；仅在需要图片时渲染，
    # 避免导出纯词频 CSV 时被词云错误连带拖垮（见 _run_export）。
    png = render_word_cloud_png(result["rows"], language, options.random_state) if include_image else None
    stored = {**result, "png": png, "options": {
        "sortBy": options.sort_by,
        "topN": options.top_n,
        "minTermFrequency": options.min_term_frequency,
        "minDocumentFrequency": options.min_document_frequency,
        "randomState": options.random_state,
    }}
    state.frequency_results[language] = stored
    state.frequency_done_languages.add(language)
    state.step_frequency_done = True
    response = {key: value for key, value in result.items()}
    response["chart"] = [
        {"word": row["word"], "value": row[options.sort_by], "termFrequency": row["term_frequency"]}
        for row in result["rows"]
    ]
    if include_image and png is not None:
        response["wordCloudPngBase64"] = base64.b64encode(png).decode("ascii")
    return response


def _selected_language(payload: Dict[str, Any]) -> str:
    state = get_state()
    requested = str(payload.get("language") or "").strip().lower()
    available = [language for language, count in _language_counts(state.documents_df).items() if count]
    if requested in LANGUAGES:
        if requested not in available:
            raise ValueError(f"当前文献表没有{LANGUAGE_LABELS[requested]}文献")
        return requested
    if len(available) == 1:
        return available[0]
    raise ValueError("混合语言项目必须明确选择 language: zh 或 en")


def _filter_model_documents(state, language: str, genre: str, min_tokens: int):
    df = state.cleaned_df.copy()
    indices = [index for index, value in enumerate(df["language"].tolist()) if value == language]
    df = df.iloc[indices].reset_index(drop=True)
    tokens = [state.tokens_list[index] for index in indices]
    if genre and genre not in {"全部文类", "全部", "__all__"}:
        if "genre" not in df.columns:
            raise ValueError("当前数据没有文类字段，无法按文类筛选")
        mask = df["genre"].fillna("").astype(str).eq(str(genre))
        selected = [index for index, keep in enumerate(mask.tolist()) if keep]
        df = df.loc[mask].reset_index(drop=True)
        tokens = [tokens[index] for index in selected]
    valid = [index for index, row in enumerate(tokens) if len(row) >= min_tokens]
    if not valid:
        raise ValueError(f"当前{LANGUAGE_LABELS[language]}筛选条件下没有有效分词文献")
    return df.iloc[valid].reset_index(drop=True), [tokens[index] for index in valid]


def _model_values(payload: Dict[str, Any], model: str, language: str) -> Dict[str, Any]:
    plural = payload.get(f"{model}Configs") or {}
    return plural.get(language) or payload.get(f"{model}Config") or payload


def _run_lda(payload: Dict[str, Any]) -> Dict[str, Any]:
    state = get_state()
    _ensure_clean(payload)
    language = _selected_language(payload)
    values = _model_values(payload, "lda", language)
    model_df, model_tokens = _filter_model_documents(state, language, str(values.get("genre") or "__all__"), 3)
    dictionary, corpus, filtered_tokens = build_corpus(
        model_tokens,
        min_doc_freq=int(values.get("minDocFreq", 2)),
        max_doc_freq_ratio=float(values.get("maxDocFreqRatio", 0.95)),
    )
    model = train_lda(
        corpus, dictionary,
        num_topics=int(values.get("numTopics", 10)),
        passes=int(values.get("passes", 20)),
        iterations=int(values.get("iterations", 400)),
        random_state=int(values.get("randomState", 42)),
    )
    topics = get_topics(model, n_words=20)
    coherence = compute_coherence(model, corpus, dictionary, filtered_tokens)
    doc_topics = get_doc_topics(model, corpus, model_df, list(range(len(filtered_tokens))))
    state.lda_results[language] = {
        "model": model, "dictionary": dictionary, "corpus": corpus, "topics": topics,
        "doc_topics": doc_topics, "coherence": coherence,
    }
    state.lda_done_languages.add(language)
    return {
        "language": language, "topicCount": len(topics), "documents": len(doc_topics),
        "topics": topics, "coherence": _number(coherence),
        "documentTopics": _preview_dataframe("ldaDocTopics", doc_topics, {"page": 1, "pageSize": 200}),
    }


def _run_stm_check() -> Dict[str, Any]:
    with contextlib.redirect_stdout(sys.stderr):
        ok, message = check_r_environment()
    get_state().r_available = ok
    return {"available": ok, "message": message}


def _run_stm(payload: Dict[str, Any]) -> Dict[str, Any]:
    state = get_state()
    _ensure_clean(payload)
    language = _selected_language(payload)
    values = _model_values(payload, "stm", language)
    model_df, model_tokens = _filter_model_documents(state, language, str(values.get("genre") or "__all__"), 2)
    r_model, topics, doc_topics, prevalence = train_stm(
        model_df, model_tokens,
        num_topics=int(values.get("numTopics", 10)),
        prevalence_formula=str(values.get("prevalenceFormula") or "~ 1"),
        content_covariate=str(values.get("contentCovariate") or "").strip() or None,
        seed=int(values.get("randomState", 42)),
        max_em_its=int(values.get("maxEmIterations", 75)),
    )
    state.stm_results[language] = {
        "model": r_model, "topics": topics, "doc_topics": doc_topics, "prevalence": prevalence,
    }
    state.stm_done_languages.add(language)
    state.r_available = True
    return {
        "language": language, "topicCount": len(topics), "documents": len(doc_topics), "topics": topics,
        "documentTopics": _preview_dataframe("stmDocTopics", doc_topics, {"page": 1, "pageSize": 200}),
        "prevalence": _json_records(prevalence),
        "prevalenceColumns": [] if prevalence is None else [str(column) for column in prevalence.columns],
    }


def _open_lda_visualization(payload: Dict[str, Any]) -> Dict[str, Any]:
    result = _run_lda(payload)
    language = result["language"]
    values = get_state().lda_results[language]
    output_dir = str(payload.get("outputDir") or get_state().output_dir or os.path.expanduser("~"))
    path = open_pyldavis(values["model"], values["corpus"], values["dictionary"], output_dir)
    return {"path": path, "language": language, "message": "pyLDAvis 已生成并在浏览器中打开"}


def _compare_summary(payload: Dict[str, Any]) -> Dict[str, Any]:
    state = get_state()
    model_name = str(payload.get("model") or "lda").lower()
    result = _run_stm(payload) if model_name == "stm" else _run_lda(payload)
    language = result["language"]
    doc_topics = (
        state.stm_results[language]["doc_topics"] if model_name == "stm"
        else state.lda_results[language]["doc_topics"]
    )
    filtered = doc_topics.copy()
    for field, selected in (payload.get("filters") or {}).items():
        if selected in (None, "", "__all__"):
            continue
        if field not in filtered.columns:
            raise ValueError(f"当前模型结果缺少筛选字段：{field}")
        filtered = filtered[filtered[field].fillna("").astype(str).eq(str(selected))]
    if filtered.empty:
        raise ValueError("当前筛选条件下没有可用于对比的文献")
    axis = str(payload.get("axisField") or "source_name")
    if axis == "language":
        raise ValueError("中英文模型彼此独立，不能使用 language 作为主题对比轴")
    if axis not in filtered.columns:
        raise ValueError(f"当前模型结果缺少聚合维度：{axis}")
    topic_columns = [column for column in filtered.columns if column.startswith("topic_")]
    metric = str(payload.get("metricField") or "__all__")
    if metric != "__all__":
        if metric not in topic_columns:
            raise ValueError(f"当前模型结果缺少主题指标：{metric}")
        topic_columns = [metric]
    summary = build_compare_summary(filtered, axis, topic_columns)
    summary["model"] = model_name
    summary["language"] = language
    summary["chartType"] = "line" if axis in {"year", "time_index"} else str(payload.get("chartType") or "bar")
    articles = representative_articles(filtered, int(payload.get("representativeLimit", 3)))
    lookup = {str(row.get("doc_id", "")): row for row in _json_records(state.documents_df)}
    for topic_articles in articles.values():
        for article in topic_articles:
            original = lookup.get(str(article.get("doc_id", "")), {})
            for field in ("text", "creator", "title", "source_name", "date", "genre", "language"):
                if article.get(field) in (None, ""):
                    article[field] = original.get(field, "")
    summary["representativeArticles"] = articles
    summary["filters"] = payload.get("filters") or {}
    return summary


def _run_compare(payload: Dict[str, Any]) -> Dict[str, Any]:
    summary = _compare_summary(payload)
    return {
        "language": summary["language"], "rows": len(summary.get("rows") or []),
        "groups": summary.get("groups") or [], "representativeArticles": summary.get("representativeArticles") or {},
        **summary,
    }


def _export_items(payload: Dict[str, Any]) -> Dict[str, Any]:
    _ensure_import(payload)
    return {"items": [
        {"key": "documents", "filename": "documents.csv", "label": "标准化文献表", "available": True},
        {"key": "cleaned_documents", "filename": "cleaned_documents.csv", "label": "清洗后文献", "available": True},
        {"key": "tokens_corpus", "filename": "{language}/tokens_corpus.txt", "label": "分语言语料", "available": True},
        {"key": "word_frequency", "filename": "{language}/word_frequency.csv", "label": "词频明细", "available": True},
        {"key": "word_cloud", "filename": "{language}/word_cloud.png", "label": "词云 PNG", "available": True},
        {"key": "lda_topic_word", "filename": "{language}/lda_topic_word.csv", "label": "LDA 主题词", "available": True},
        {"key": "lda_doc_topic", "filename": "{language}/lda_doc_topic.csv", "label": "LDA 文献主题", "available": True},
        {"key": "lda_coherence", "filename": "{language}/lda_coherence.json", "label": "LDA 一致性", "available": True},
        {"key": "stm_topic_word", "filename": "{language}/stm_topic_word.csv", "label": "STM 主题词", "available": True},
        {"key": "stm_doc_topic", "filename": "{language}/stm_doc_topic.csv", "label": "STM 文献主题", "available": True},
        {"key": "stm_prevalence", "filename": "{language}/stm_topic_prevalence.csv", "label": "STM prevalence", "available": True},
        {"key": "session_config", "filename": "session_config.json", "label": "v2 会话配置", "available": True},
    ]}


def _run_export(payload: Dict[str, Any]) -> Dict[str, Any]:
    state = get_state()
    _ensure_clean(payload)
    output_dir = str(payload.get("outputDir") or "").strip()
    if not output_dir:
        raise ValueError("请选择导出目录")
    os.makedirs(output_dir, exist_ok=True)
    state.output_dir = output_dir
    state.project_name = str(payload.get("projectName") or state.project_name)
    default_items = {
        "documents", "cleaned_documents", "tokens_corpus", "lda_topic_word", "lda_doc_topic",
        "word_frequency", "word_cloud", "lda_coherence", "stm_topic_word", "stm_doc_topic",
        "stm_prevalence", "session_config",
    }
    selected = set(payload.get("exportItems") or default_items)
    available_languages = [language for language, count in _language_counts(state.documents_df).items() if count]
    requested_languages = payload.get("exportLanguages") or available_languages
    languages = [language for language in requested_languages if language in available_languages]
    exported, errors = [], []

    def write_common(key, filename, action):
        if key not in selected:
            return
        try:
            action()
            exported.append(filename)
        except Exception as exc:
            errors.append({"key": key, "language": None, "error": str(exc)})

    write_common("documents", "documents.csv", lambda: state.documents_df.to_csv(
        os.path.join(output_dir, "documents.csv"), index=False, encoding="utf-8-sig"
    ))
    write_common("cleaned_documents", "cleaned_documents.csv", lambda: state.cleaned_df.to_csv(
        os.path.join(output_dir, "cleaned_documents.csv"), index=False, encoding="utf-8-sig"
    ))

    lda_keys = {"lda_topic_word", "lda_doc_topic", "lda_coherence"}
    stm_keys = {"stm_topic_word", "stm_doc_topic", "stm_prevalence"}
    for language in languages:
        language_dir = os.path.join(output_dir, language)
        os.makedirs(language_dir, exist_ok=True)
        indices = [i for i, value in enumerate(state.cleaned_df["language"].tolist()) if value == language]
        language_tokens = [state.tokens_list[index] for index in indices]
        if "tokens_corpus" in selected:
            try:
                with open(os.path.join(language_dir, "tokens_corpus.txt"), "w", encoding="utf-8") as file:
                    for tokens in language_tokens:
                        file.write(" ".join(tokens) + "\n")
                exported.append(f"{language}/tokens_corpus.txt")
            except Exception as exc:
                errors.append({"key": "tokens_corpus", "language": language, "error": str(exc)})

        frequency_keys = selected & {"word_frequency", "word_cloud"}
        if frequency_keys:
            # 先做一次不含图片的词频分析拿到 rows；词频 CSV 与词云 PNG
            # 各自独立写出，缺少中文字体等词云错误不应连带 CSV 一起失败。
            frequency_rows = None
            try:
                result = _run_frequency({**payload, "language": language}, include_image=False)
                frequency_rows = result["rows"]
            except Exception as exc:
                for key in sorted(frequency_keys):
                    errors.append({"key": key, "language": language, "error": str(exc)})
            if frequency_rows is not None:
                if "word_frequency" in selected:
                    try:
                        exported.extend(
                            write_frequency_outputs(language_dir, frequency_rows, None, {"word_frequency"})
                        )
                    except Exception as exc:
                        errors.append({"key": "word_frequency", "language": language, "error": str(exc)})
                if "word_cloud" in selected:
                    try:
                        png = render_word_cloud_png(
                            frequency_rows, language, _frequency_options(payload, language).random_state
                        )
                        exported.extend(
                            write_frequency_outputs(language_dir, frequency_rows, png, {"word_cloud"})
                        )
                    except Exception as exc:
                        errors.append({"key": "word_cloud", "language": language, "error": str(exc)})

        if selected & lda_keys:
            try:
                _run_lda({**payload, "language": language})
                values = state.lda_results[language]
                if "lda_topic_word" in selected:
                    rows = [
                        {"topic_id": topic["topic_id"], "rank": rank, "word": word, "probability": probability}
                        for topic in values["topics"] for rank, (word, probability) in enumerate(topic["words"], 1)
                    ]
                    pd.DataFrame(rows).to_csv(os.path.join(language_dir, "lda_topic_word.csv"), index=False, encoding="utf-8-sig")
                    exported.append(f"{language}/lda_topic_word.csv")
                if "lda_doc_topic" in selected:
                    values["doc_topics"].to_csv(os.path.join(language_dir, "lda_doc_topic.csv"), index=False, encoding="utf-8-sig")
                    exported.append(f"{language}/lda_doc_topic.csv")
                if "lda_coherence" in selected:
                    with open(os.path.join(language_dir, "lda_coherence.json"), "w", encoding="utf-8") as file:
                        json.dump(
                            {"language": language, "coherence_c_v": _number(values["coherence"])},
                            file, ensure_ascii=False, indent=2,
                        )
                    exported.append(f"{language}/lda_coherence.json")
            except Exception as exc:
                for key in sorted(selected & lda_keys):
                    errors.append({"key": key, "language": language, "error": str(exc)})

        if selected & stm_keys:
            try:
                _run_stm({**payload, "language": language})
                values = state.stm_results[language]
                if "stm_topic_word" in selected:
                    rows = [
                        {"topic_id": topic["topic_id"], "rank": rank, "word": word}
                        for topic in values["topics"] for rank, (word, _) in enumerate(topic["words"], 1)
                    ]
                    pd.DataFrame(rows).to_csv(os.path.join(language_dir, "stm_topic_word.csv"), index=False, encoding="utf-8-sig")
                    exported.append(f"{language}/stm_topic_word.csv")
                if "stm_doc_topic" in selected:
                    values["doc_topics"].to_csv(os.path.join(language_dir, "stm_doc_topic.csv"), index=False, encoding="utf-8-sig")
                    exported.append(f"{language}/stm_doc_topic.csv")
                if "stm_prevalence" in selected and values["prevalence"] is not None:
                    values["prevalence"].to_csv(os.path.join(language_dir, "stm_topic_prevalence.csv"), index=False, encoding="utf-8-sig")
                    exported.append(f"{language}/stm_topic_prevalence.csv")
            except Exception as exc:
                for key in sorted(selected & stm_keys):
                    errors.append({"key": key, "language": language, "error": str(exc)})

    def write_session():
        config = dict(state.session_payload)
        config.update({
            "schemaVersion": 2,
            "projectName": state.project_name,
            "outputDir": output_dir,
            "exportedAt": datetime.now().isoformat(),
            "documentCount": len(state.documents_df),
            "languageRows": _language_counts(state.documents_df),
            "fieldMapping": state.document_col_map,
            "frequencyCompletedLanguages": sorted(state.frequency_done_languages),
        })
        with open(os.path.join(output_dir, "session_config.json"), "w", encoding="utf-8") as file:
            json.dump(config, file, ensure_ascii=False, indent=2)

    write_common("session_config", "session_config.json", write_session)
    return {"outputDir": output_dir, "exported": exported, "errors": errors, "count": len(exported)}


def _table_preview(payload: Dict[str, Any]) -> Dict[str, Any]:
    table = str(payload.get("table") or payload.get("source") or "documents")
    state = get_state()
    if table == "documents":
        _ensure_import(payload)
        frame = state.documents_df
    elif table == "cleaned":
        _ensure_clean(payload)
        frame = state.cleaned_df
    elif table in {"ldaDocTopics", "stmDocTopics"}:
        result = _run_lda(payload) if table.startswith("lda") else _run_stm(payload)
        language = result["language"]
        frame = state.lda_results[language]["doc_topics"] if table.startswith("lda") else state.stm_results[language]["doc_topics"]
    else:
        raise ValueError(f"不支持的表格预览来源：{table}")
    return _preview_dataframe(table, frame, payload)


def _stm_covariates(payload: Dict[str, Any]) -> Dict[str, Any]:
    _ensure_import(payload)
    return {"covariates": _covariate_items(get_state().documents_df)}


def handle(command: str, payload: Dict[str, Any]) -> Dict[str, Any]:
    if command in {"task.import", "import.load_documents"}:
        reset_state()
    elif command in {"task.clean", "clean.run"} and get_state().step_cleaned:
        state = get_state()
        state.cleaned_df = None
        state.tokens_list = None
        state.frequency_results.clear()
        state.lda_results.clear()
        state.stm_results.clear()
        state.frequency_done_languages.clear()
        state.lda_done_languages.clear()
        state.stm_done_languages.clear()
        state.step_frequency_done = False
        state.step_lda_done = False
        state.step_stm_done = False
    _remember_session_payload(payload)
    if command == "session.get_state":
        data = {}
    elif command in {"task.import", "import.load_documents"}:
        data = _ensure_import(payload)
    elif command in {"task.clean", "clean.run"}:
        data = _ensure_clean(payload)
    elif command in {"task.frequency", "frequency.analyze"}:
        data = _run_frequency(payload)
    elif command in {"task.lda", "lda.train"}:
        data = _run_lda(payload)
    elif command == "lda.open_pyldavis":
        data = _open_lda_visualization(payload)
    elif command in {"task.stm", "stm.train"}:
        data = _run_stm(payload)
    elif command == "stm.check_r":
        data = _run_stm_check()
    elif command == "table.preview":
        data = _table_preview(payload)
    elif command == "clean.preview":
        data = _ensure_clean(payload)
    elif command == "lda.get_result":
        data = _run_lda(payload)
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
        result = handle(args.command, json.loads(args.payload))
    except Exception as exc:
        error = {
            "code": exc.__class__.__name__.upper(),
            "message": str(exc),
            "recoverable": True,
            "suggestion": "请检查文献表必填字段、语言值、清洗参数和外部运行环境。",
        }
        if isinstance(exc, DocumentValidationError):
            error["code"] = "INVALID_DOCUMENT_TABLE"
            error["issues"] = exc.issues
        result = {"ok": False, "error": error, "state": _state_snapshot()}
    sys.stdout.write(json.dumps(_json_safe(result), ensure_ascii=False))
    return 0 if result.get("ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())
