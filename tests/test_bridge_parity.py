import json
from datetime import datetime

import pandas as pd
import pytest

import backend.bridge as bridge
from models.app_state import get_state, reset_state


@pytest.fixture(autouse=True)
def _reset_bridge_state():
    reset_state()
    yield
    reset_state()


def _write_real_tables(tmp_path):
    metadata_path = tmp_path / "metadata.csv"
    text_path = tmp_path / "text.csv"
    pd.DataFrame([
        {"文档编号": "001", "标题": "甲文", "报刊名": "申报", "出版日期": "1931-01-05", "文类": "新闻"},
        {"文档编号": "002", "标题": "乙文", "报刊名": "大公报", "出版日期": "1932-03-12", "文类": "评论"},
        {"文档编号": "003", "标题": "丙文", "报刊名": "申报", "出版日期": "1933-08-18", "文类": "新闻"},
    ]).to_csv(metadata_path, index=False, encoding="utf-8")
    pd.DataFrame([
        {"文章编号": "001", "正文": "甲文 保留词 测试文本"},
        {"文章编号": "002", "正文": "乙文 另一篇 测试文本"},
        {"文章编号": "003", "正文": "丙文 第三篇 测试文本"},
    ]).to_csv(text_path, index=False, encoding="utf-8")
    return metadata_path, text_path


def _import_payload(metadata_path, text_path, **extra):
    return {
        "metadataPath": str(metadata_path),
        "textPath": str(text_path),
        "metadataIdField": "文档编号",
        "textIdField": "文章编号",
        **extra,
    }


def test_real_import_returns_detected_mappings_preview_and_genres(tmp_path):
    metadata_path, text_path = _write_real_tables(tmp_path)

    response = bridge.handle("task.import", _import_payload(metadata_path, text_path))

    assert response["ok"] is True
    data = response["data"]
    assert data["metadataMapping"]["doc_id"] == "文档编号"
    assert data["metadataMapping"]["article_title"] == "标题"
    assert data["metadataMapping"]["genre"] == "文类"
    assert data["textMapping"] == {"doc_id": "文章编号", "text": "正文"}
    assert data["genres"] == sorted(["新闻", "评论"])

    preview = data["preview"]
    assert preview["table"] == "merged"
    assert preview["total"] == 3
    assert preview["pageSize"] == 10
    assert [row["doc_id"] for row in preview["rows"]] == ["001", "002", "003"]
    assert preview["rows"][0]["article_title"] == "甲文"
    assert preview["rows"][0]["genre"] == "新闻"
    assert preview["rows"][0]["text"] == "甲文 保留词 测试文本"


def test_task_import_rejects_missing_real_file_paths(tmp_path):
    metadata_path, _ = _write_real_tables(tmp_path)

    with pytest.raises(ValueError, match="未找到已导入的真实文件"):
        bridge.handle("task.import", {})

    with pytest.raises(ValueError, match="未找到已导入的真实文件"):
        bridge.handle("task.import", {"metadataPath": str(metadata_path)})


def test_clean_result_has_parity_columns_and_allows_empty_stopwords(monkeypatch, tmp_path):
    metadata_path, text_path = _write_real_tables(tmp_path)
    captured = {}

    def fake_tokenize(texts, options, stopwords, custom_dict_path):
        captured["texts"] = list(texts)
        captured["stopwords"] = set(stopwords)
        captured["custom_dict_path"] = custom_dict_path
        tokens = [
            ["甲文", "保留词", "测试文本"],
            ["乙文", "另一篇", "测试文本"],
            ["丙文", "第三篇", "测试文本"],
        ]
        return tokens, {
            "total_docs": len(tokens),
            "non_empty_docs": len(tokens),
            "total_tokens": sum(len(row) for row in tokens),
            "unique_words": len({word for row in tokens for word in row}),
        }

    monkeypatch.setattr(bridge, "tokenize_texts", fake_tokenize)
    payload = _import_payload(
        metadata_path,
        text_path,
        useDefaultStopwords=False,
        stopwords=[],
        options={
            "removeEmpty": False,
            "removeDuplicates": False,
            "ocrClean": False,
            "removePunct": False,
            "removeNumbers": False,
            "traditionalToSimplified": False,
            "minTextLength": 1,
            "minTokenFreq": 1,
            "minDocFreq": 1,
            "maxDocFreqRatio": 1.0,
        },
    )

    response = bridge.handle("task.clean", payload)

    assert response["ok"] is True
    assert captured["stopwords"] == set()
    assert response["data"]["stopwordCount"] == 0
    assert response["state"]["session"]["payload"]["useDefaultStopwords"] is False
    assert response["state"]["session"]["payload"]["stopwords"] == []

    preview = response["data"]["preview"]
    assert {"cleaned_text", "tokens", "token_count"}.issubset(preview["columns"])
    assert [row["cleaned_text"] for row in preview["rows"]] == captured["texts"]
    assert preview["rows"][0]["tokens"] == "甲文 保留词 测试文本"
    assert preview["rows"][0]["token_count"] == 3


def test_lda_genre_filter_keeps_metadata_aligned_across_middle_empty_tokens(monkeypatch):
    state = get_state()
    state.cleaned_df = pd.DataFrame([
        {"doc_id": "A", "genre": "新闻", "article_title": "首篇"},
        {"doc_id": "B", "genre": "新闻", "article_title": "中间空词篇"},
        {"doc_id": "C", "genre": "评论", "article_title": "其他文类"},
        {"doc_id": "D", "genre": "新闻", "article_title": "末篇"},
    ])
    state.merged_df = state.cleaned_df.copy()
    state.tokens_list = [
        ["甲一", "甲二", "甲三"],
        [],
        ["丙一", "丙二", "丙三"],
        ["丁一", "丁二", "丁三"],
    ]
    state.step_cleaned = True
    captured = {}

    def fake_build_corpus(tokens, **kwargs):
        captured["model_tokens"] = tokens
        return "dictionary", ["bow-A", "bow-D"], tokens

    def fake_get_doc_topics(model, corpus, model_df, filtered_indices):
        captured["metadata_doc_ids"] = model_df["doc_id"].tolist()
        captured["filtered_indices"] = filtered_indices
        result = model_df[["doc_id", "genre", "article_title"]].copy()
        result["topic_0"] = [0.8, 0.2]
        result["dominant_topic"] = ["主题0", "主题0"]
        return result

    monkeypatch.setattr(bridge, "build_corpus", fake_build_corpus)
    monkeypatch.setattr(bridge, "train_lda", lambda *args, **kwargs: object())
    monkeypatch.setattr(bridge, "get_topics", lambda model, n_words: [
        {"topic_id": 0, "words": [("测试", 1.0)], "label": "主题1: 测试"},
    ])
    monkeypatch.setattr(bridge, "compute_coherence", lambda *args, **kwargs: 0.5)
    monkeypatch.setattr(bridge, "get_doc_topics", fake_get_doc_topics)

    result = bridge._run_lda({
        "genre": "新闻",
        "numTopics": 1,
        "passes": 1,
        "iterations": 10,
        "minDocFreq": 1,
        "maxDocFreqRatio": 1.0,
    })

    assert captured["model_tokens"] == [
        ["甲一", "甲二", "甲三"],
        ["丁一", "丁二", "丁三"],
    ]
    assert captured["metadata_doc_ids"] == ["A", "D"]
    assert captured["filtered_indices"] == [0, 1]
    assert [row["doc_id"] for row in result["documentTopics"]["rows"]] == ["A", "D"]
    assert result["genre"] == "新闻"


def test_selective_export_reports_successes_errors_and_compatible_session(monkeypatch, tmp_path):
    metadata_path, text_path = _write_real_tables(tmp_path)
    output_dir = tmp_path / "selected-export"

    def fail_lda(_payload):
        raise RuntimeError("测试中的 LDA 结果不可用")

    monkeypatch.setattr(bridge, "_run_lda", fail_lda)
    response = bridge.handle("task.export", _import_payload(
        metadata_path,
        text_path,
        projectName="桌面版兼容项目",
        outputDir=str(output_dir),
        exportItems=["merged_data", "lda_coherence", "session_config"],
    ))

    assert response["ok"] is True
    data = response["data"]
    assert data["exported"] == ["merged_data.csv", "session_config.json"]
    assert data["count"] == 2
    assert data["errors"] == [{
        "key": "lda_coherence",
        "label": "LDA 结果",
        "error": "测试中的 LDA 结果不可用",
    }]
    assert (output_dir / "merged_data.csv").exists()
    assert not (output_dir / "lda_coherence.json").exists()

    session = json.loads((output_dir / "session_config.json").read_text(encoding="utf-8"))
    assert session["projectName"] == "桌面版兼容项目"
    assert session["outputDir"] == str(output_dir)
    assert session["project_name"] == "桌面版兼容项目"
    assert session["output_dir"] == str(output_dir)
    assert session["article_count"] == 3
    assert session["lda_done"] is False
    assert session["stm_done"] is False
    datetime.fromisoformat(session["exported_at"])
