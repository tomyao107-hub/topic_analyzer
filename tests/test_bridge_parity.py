import json

import pandas as pd
import pytest

import backend.bridge as bridge
from models.app_state import get_state, reset_state
from services.data_service import DocumentValidationError, load_documents


@pytest.fixture(autouse=True)
def _reset_bridge_state():
    reset_state()
    yield
    reset_state()


def _document_rows():
    return [
        {"文献编号": "Z1", "题名": "市场与工厂", "来源": "申报", "日期": "1931-01-05", "语种": "中文", "正文": "市场 贸易 工厂 工人 生产 商品 价格", "研究分组": "城市"},
        {"文献编号": "Z2", "题名": "学校新制", "来源": "大公报", "日期": "1932-03-12", "语种": "Chinese", "正文": "学校 教育 学生 课程 教师 新制 学习", "研究分组": "教育"},
        {"文献编号": "Z3", "题名": "乡村建设", "来源": "民国日报", "日期": "1933-08-18", "语种": "zh-CN", "正文": "乡村 建设 农民 合作 水利 土地 农业", "研究分组": "乡村"},
        {"文献编号": "E1", "题名": "Factory markets", "来源": "The Times", "日期": "1931-02-04", "语种": "英文", "正文": "The inter-\nnational markets preserved workers' histories.", "研究分组": "urban"},
        {"文献编号": "E2", "题名": "School reform", "来源": "The Guardian", "日期": "1932-04-13", "语种": "English", "正文": "Schools and teachers discussed education reforms in public.", "研究分组": "education"},
        {"文献编号": "E3", "题名": "Rural works", "来源": "Daily News", "日期": "1933-09-19", "语种": "en-GB", "正文": "Rural farmers built water works and cooperative markets.", "研究分组": "rural"},
    ]


def _write_documents(tmp_path, suffix="csv"):
    path = tmp_path / f"documents.{suffix}"
    frame = pd.DataFrame(_document_rows())
    if suffix == "xlsx":
        frame.to_excel(path, index=False)
    else:
        frame.to_csv(path, index=False, encoding="utf-8")
    return path


def _payload(path, **extra):
    return {
        "dataPath": str(path),
        "fieldMapping": {"doc_id": "文献编号", "text": "正文", "language": "语种"},
        **extra,
    }


@pytest.mark.parametrize("suffix", ["csv", "xlsx"])
def test_single_table_import_normalizes_aliases_languages_dates_and_custom_fields(tmp_path, suffix):
    path = _write_documents(tmp_path, suffix)
    response = bridge.handle("task.import", _payload(path))

    assert response["ok"] is True
    data = response["data"]
    assert data["documentRows"] == 6
    assert data["languageRows"] == {"zh": 3, "en": 3}
    assert data["mapping"]["title"] == "题名"
    assert data["mapping"]["source_name"] == "来源"
    assert "研究分组" in data["unrecognizedColumns"]
    first = data["preview"]["rows"][0]
    assert first["title"] == "市场与工厂"
    assert first["source_name"] == "申报"
    assert first["language"] == "zh"
    assert first["year"] == 1931
    assert first["研究分组"] == "城市"


@pytest.mark.parametrize(
    ("mutate", "issue_type", "expected_rows"),
    [
        (lambda rows: rows.__setitem__(1, {**rows[1], "文献编号": "Z1"}), "duplicate_doc_id", [2, 3]),
        (lambda rows: rows.__setitem__(0, {**rows[0], "正文": ""}), "blank_required_value", [2]),
        (lambda rows: rows.__setitem__(4, {**rows[4], "语种": "fr"}), "unsupported_language", [6]),
    ],
)
def test_import_blocks_invalid_required_values_with_spreadsheet_rows(tmp_path, mutate, issue_type, expected_rows):
    rows = _document_rows()
    mutate(rows)
    path = tmp_path / "invalid.csv"
    pd.DataFrame(rows).to_csv(path, index=False, encoding="utf-8")

    with pytest.raises(DocumentValidationError) as caught:
        load_documents(str(path), {"doc_id": "文献编号", "text": "正文", "language": "语种"})

    issue = next(item for item in caught.value.issues if item["type"] == issue_type)
    assert issue["rows"][: len(expected_rows)] == expected_rows


def test_import_blocks_missing_language_column(tmp_path):
    path = tmp_path / "missing.csv"
    pd.DataFrame(_document_rows()).drop(columns=["语种"]).to_csv(path, index=False, encoding="utf-8")
    with pytest.raises(DocumentValidationError) as caught:
        load_documents(str(path), {"doc_id": "文献编号", "text": "正文"})
    assert caught.value.issues[0]["type"] == "missing_columns"
    assert caught.value.issues[0]["columns"] == ["language"]


def test_language_aware_cleaning_preserves_original_and_reports_language_stats(tmp_path):
    path = _write_documents(tmp_path)
    response = bridge.handle("task.clean", _payload(
        path,
        cleanConfig={
            "removeEmpty": True,
            "removeDuplicates": False,
            "ocrClean": True,
            "removePunct": True,
            "removeNumbers": True,
            "minTextLength": 1,
            "minTokenFreq": 1,
            "zh": {"useDefaultStopwords": True, "stopwords": [], "minTokenLength": 1},
            "en": {"useDefaultStopwords": True, "stopwords": [], "minTokenLength": 2, "lowercase": True, "repairHyphenation": True},
        },
    ))

    assert response["ok"] is True
    assert response["data"]["languages"]["zh"]["documents"] == 3
    assert response["data"]["languages"]["en"]["documents"] == 3
    rows = response["data"]["preview"]["rows"]
    english = next(row for row in rows if row["doc_id"] == "E1")
    assert "inter-\nnational" in english["text"]
    assert "international" in english["cleaned_text"]
    assert "the" not in english["tokens"].split()
    assert "markets" in english["tokens"].split()
    assert "market" not in english["tokens"].split()  # 不做词形还原
    assert all(row["language"] in {"zh", "en"} for row in rows)


def test_lda_results_are_isolated_by_language_and_metadata_stays_aligned(monkeypatch, tmp_path):
    path = _write_documents(tmp_path)
    bridge.handle("task.clean", _payload(path, cleanConfig={"minTextLength": 1, "removeDuplicates": False, "zh": {}, "en": {}}))

    captured = []

    def fake_build(tokens, **_kwargs):
        captured.append(tokens)
        return object(), [f"bow-{index}" for index in range(len(tokens))], tokens

    def fake_doc_topics(_model, corpus, model_df, _indices):
        result = model_df.drop(columns=[column for column in ("text", "cleaned_text", "tokens", "token_count") if column in model_df]).copy()
        result["topic_0"] = [1.0] * len(corpus)
        result["dominant_topic"] = "主题1"
        return result

    monkeypatch.setattr(bridge, "build_corpus", fake_build)
    monkeypatch.setattr(bridge, "train_lda", lambda *args, **kwargs: object())
    monkeypatch.setattr(bridge, "get_topics", lambda *_args, **_kwargs: [{"topic_id": 0, "words": [("word", 1.0)], "label": "主题1"}])
    monkeypatch.setattr(bridge, "compute_coherence", lambda *_args, **_kwargs: 0.5)
    monkeypatch.setattr(bridge, "get_doc_topics", fake_doc_topics)

    zh = bridge._run_lda({"language": "zh", "numTopics": 1, "minDocFreq": 1, "maxDocFreqRatio": 1.0})
    en = bridge._run_lda({"language": "en", "numTopics": 1, "minDocFreq": 1, "maxDocFreqRatio": 1.0})

    state = get_state()
    assert set(state.lda_results) == {"zh", "en"}
    assert {row["language"] for row in zh["documentTopics"]["rows"]} == {"zh"}
    assert {row["language"] for row in en["documentTopics"]["rows"]} == {"en"}
    assert all(len(tokens) == 3 for tokens in captured)


def test_stm_results_are_isolated_by_language(monkeypatch, tmp_path):
    path = _write_documents(tmp_path)
    bridge.handle("task.clean", _payload(path, cleanConfig={"minTextLength": 1, "removeDuplicates": False, "zh": {}, "en": {}}))

    def fake_train(model_df, _tokens, **_kwargs):
        doc_topics = model_df.drop(columns=[column for column in ("text", "cleaned_text", "tokens", "token_count") if column in model_df]).copy()
        doc_topics["topic_0"] = 1.0
        doc_topics["dominant_topic"] = "主题1"
        return object(), [{"topic_id": 0, "words": [("word", 0.0)]}], doc_topics, pd.DataFrame()

    monkeypatch.setattr(bridge, "train_stm", fake_train)
    zh = bridge._run_stm({"language": "zh", "numTopics": 1, "prevalenceFormula": "~ 1"})
    en = bridge._run_stm({"language": "en", "numTopics": 1, "prevalenceFormula": "~ 1"})

    assert set(get_state().stm_results) == {"zh", "en"}
    assert {row["language"] for row in zh["documentTopics"]["rows"]} == {"zh"}
    assert {row["language"] for row in en["documentTopics"]["rows"]} == {"en"}


def test_export_uses_common_files_and_language_directories(monkeypatch, tmp_path):
    path = _write_documents(tmp_path)
    output = tmp_path / "export"

    def fake_run_lda(payload):
        language = payload["language"]
        state = get_state()
        frame = state.cleaned_df[state.cleaned_df["language"] == language][["doc_id", "language"]].reset_index(drop=True)
        frame["topic_0"] = 1.0
        state.lda_results[language] = {
            "topics": [{"topic_id": 0, "words": [("word", 1.0)]}],
            "doc_topics": frame,
            "coherence": 0.5,
        }
        return {"language": language}

    monkeypatch.setattr(bridge, "_run_lda", fake_run_lda)
    response = bridge.handle("task.export", _payload(
        path,
        projectName="v2 回归测试",
        outputDir=str(output),
        exportLanguages=["zh", "en"],
        exportItems=["documents", "cleaned_documents", "tokens_corpus", "lda_topic_word", "lda_doc_topic", "lda_coherence", "session_config"],
        cleanConfig={"minTextLength": 1, "removeDuplicates": False, "zh": {}, "en": {}},
    ))

    assert response["ok"] is True
    assert (output / "documents.csv").exists()
    assert (output / "cleaned_documents.csv").exists()
    assert (output / "zh" / "tokens_corpus.txt").exists()
    assert (output / "en" / "lda_doc_topic.csv").exists()
    session = json.loads((output / "session_config.json").read_text(encoding="utf-8"))
    assert session["schemaVersion"] == 2
    assert session["languageRows"] == {"zh": 3, "en": 3}
    assert session["fieldMapping"]["language"] == "语种"
