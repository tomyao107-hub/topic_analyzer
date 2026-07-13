import base64

import pandas as pd
import pytest

import services.frequency_service as frequency_service
from backend.bridge import handle
from models.app_state import get_state, reset_state
from services.frequency_service import (
    FrequencyAnalysisError,
    FrequencyOptions,
    analyze_word_frequency,
    find_cjk_font_path,
    render_word_cloud_png,
)


def test_frequency_counts_ratios_filters_and_stable_order():
    result = analyze_word_frequency(
        [["市场", "贸易", "市场"], ["市场", "工厂", "贸易"]],
        FrequencyOptions(language="zh", sort_by="term_frequency", top_n=3),
    )
    assert [row["word"] for row in result["rows"]] == ["市场", "贸易", "工厂"]
    assert result["rows"][0] == {
        "rank": 1, "word": "市场", "term_frequency": 3, "document_frequency": 2,
        "document_frequency_ratio": 1.0, "token_share": 0.5,
    }
    filtered = analyze_word_frequency(
        [["b", "a"], ["a", "b"]],
        FrequencyOptions(language="en", sort_by="document_frequency", top_n=1, min_term_frequency=2),
    )
    assert filtered["rows"][0]["word"] == "a"


def test_frequency_rejects_empty_and_filtered_corpora():
    with pytest.raises(FrequencyAnalysisError, match="没有已清洗文献"):
        analyze_word_frequency([], FrequencyOptions(language="en"))
    with pytest.raises(FrequencyAnalysisError, match="过滤后没有词语"):
        analyze_word_frequency([["only"]], FrequencyOptions(language="en", min_term_frequency=2))


def test_word_cloud_is_a_png_and_chinese_font_is_discoverable_on_windows():
    rows = [{"word": "history", "term_frequency": 4}, {"word": "market", "term_frequency": 2}]
    png = render_word_cloud_png(rows, "en")
    assert png.startswith(b"\x89PNG\r\n\x1a\n")
    assert len(png) > 1000
    if find_cjk_font_path():
        assert render_word_cloud_png([{"word": "历史", "term_frequency": 2}], "zh").startswith(b"\x89PNG")


def test_chinese_word_cloud_reports_missing_font(monkeypatch):
    monkeypatch.setattr(frequency_service, "find_cjk_font_path", lambda *_args, **_kwargs: "")
    with pytest.raises(FrequencyAnalysisError, match="中文字体"):
        render_word_cloud_png([{"word": "历史", "term_frequency": 2}], "zh")


def test_bridge_frequency_is_bilingual_and_reclean_invalidates_results(tmp_path):
    source = pd.DataFrame([
        {"doc_id": "Z1", "text": "市场 贸易 市场", "language": "zh"},
        {"doc_id": "E1", "text": "markets trade markets", "language": "en"},
    ])
    path = tmp_path / "双语 样例.csv"
    source.to_csv(path, index=False, encoding="utf-8")
    payload = {
        "dataPath": str(path),
        "fieldMapping": {"doc_id": "doc_id", "text": "text", "language": "language"},
        "cleanConfig": {
            "minTextLength": 1, "removeDuplicates": False,
            "zh": {"useDefaultStopwords": False}, "en": {"useDefaultStopwords": False},
        },
        "topN": 10,
    }
    reset_state()
    zh = handle("task.frequency", {**payload, "language": "zh"})
    en = handle("task.frequency", {**payload, "language": "en"})
    assert zh["data"]["rows"][0]["word"] == "市场"
    assert en["data"]["rows"][0]["word"] == "markets"
    assert base64.b64decode(en["data"]["wordCloudPngBase64"]).startswith(b"\x89PNG")
    assert set(get_state().frequency_results) == {"zh", "en"}
    handle("task.clean", payload)
    assert get_state().frequency_results == {}


def test_export_writes_frequency_csv_png_and_session_config(tmp_path):
    source = tmp_path / "documents.csv"
    pd.DataFrame([
        {"doc_id": "E1", "text": "markets trade markets", "language": "en"},
        {"doc_id": "E2", "text": "markets factories", "language": "en"},
    ]).to_csv(source, index=False, encoding="utf-8")
    output = tmp_path / "export"
    response = handle("task.export", {
        "dataPath": str(source), "outputDir": str(output), "exportLanguages": ["en"],
        "exportItems": ["word_frequency", "word_cloud", "session_config"],
        "fieldMapping": {"doc_id": "doc_id", "text": "text", "language": "language"},
        "cleanConfig": {"minTextLength": 1, "removeDuplicates": False, "en": {"useDefaultStopwords": False}},
        "frequencyConfigs": {"en": {"topN": 20, "sortBy": "term_frequency", "minTermFrequency": 1, "minDocumentFrequency": 1}},
    })
    assert response["ok"] is True
    csv_path = output / "en" / "word_frequency.csv"
    assert csv_path.read_bytes().startswith(b"\xef\xbb\xbf")
    assert list(pd.read_csv(csv_path).columns) == [
        "rank", "word", "term_frequency", "document_frequency", "document_frequency_ratio", "token_share"
    ]
    assert (output / "en" / "word_cloud.png").read_bytes().startswith(b"\x89PNG")
    session = (output / "session_config.json").read_text(encoding="utf-8")
    assert '"frequencyConfigs"' in session
    assert '"frequencyCompletedLanguages": [' in session


def test_missing_stm_environment_is_reported_without_changing_frequency_state(monkeypatch):
    import backend.bridge as bridge

    reset_state()
    get_state().frequency_done_languages.add("zh")
    monkeypatch.setattr(bridge, "check_r_environment", lambda: (False, "R 或 stm 未安装"))
    response = bridge.handle("stm.check_r", {})
    assert response["ok"] is True
    assert response["data"] == {"available": False, "message": "R 或 stm 未安装"}
    assert get_state().frequency_done_languages == {"zh"}
