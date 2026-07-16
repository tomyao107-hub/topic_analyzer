import pandas as pd
import pytest

from backend.bridge import handle
from models.app_state import get_state, reset_state
from services.sentiment_service import (
    SentimentAnalysisError,
    SentimentOptions,
    analyze_sentiment,
    load_lexicon,
)


def test_bundled_lexicons_load_for_both_languages():
    zh = load_lexicon("zh")
    en = load_lexicon("en")
    assert len(zh.scores) > 1000
    assert len(en.scores) > 1000
    assert zh.negations  # 否定词表非空
    assert zh.polarity("繁荣") > 0
    assert zh.polarity("灾难") < 0
    assert en.polarity("good") > 0
    assert en.polarity("terrible") < 0


def test_negation_flips_and_degree_scales_scores():
    positive = analyze_sentiment([["市场", "繁荣", "希望"]], SentimentOptions(language="zh"))
    assert positive["rows"][0]["sentiment"] == "positive"
    assert positive["rows"][0]["score"] > 0

    negated = analyze_sentiment([["市场", "不", "繁荣"]], SentimentOptions(language="zh"))
    assert negated["rows"][0]["sentiment"] == "negative"

    # 否定只作用于最近的情感词，后续负面词不应被反向翻正
    scoped = analyze_sentiment(
        [["not", "good", "war", "crisis"]], SentimentOptions(language="en")
    )
    assert scoped["rows"][0]["sentiment"] == "negative"
    assert "good" in scoped["rows"][0]["negative_terms"]


def test_custom_dictionary_changes_result():
    baseline = analyze_sentiment([["中庸", "普通"]], SentimentOptions(language="zh"))
    assert baseline["rows"][0]["sentiment"] == "neutral"
    boosted = analyze_sentiment(
        [["中庸", "普通"]], SentimentOptions(language="zh", positive_words=("普通",))
    )
    assert boosted["rows"][0]["sentiment"] == "positive"


def test_sentiment_rejects_empty_corpus():
    with pytest.raises(SentimentAnalysisError, match="没有已清洗文献"):
        analyze_sentiment([], SentimentOptions(language="en"))
    with pytest.raises(SentimentAnalysisError, match="阈值"):
        SentimentOptions(language="zh", positive_threshold=-0.5, negative_threshold=0.5).validate()


def test_aggregation_groups_by_metadata_field():
    result = analyze_sentiment(
        [["繁荣", "希望"], ["灾难", "危机"], ["报道"]],
        SentimentOptions(language="zh", group_by="genre"),
        doc_ids=["A", "B", "C"],
        metadata=[{"genre": "社论"}, {"genre": "社论"}, {"genre": "新闻"}],
    )
    groups = {row["group"]: row for row in result["aggregation"]}
    assert groups["社论"]["documents"] == 2
    assert groups["社论"]["positive"] == 1
    assert groups["社论"]["negative"] == 1
    assert groups["新闻"]["documents"] == 1


def test_bridge_sentiment_is_bilingual_and_reclean_invalidates_results(tmp_path):
    source = pd.DataFrame([
        {"doc_id": "Z1", "text": "市场 繁荣 希望", "language": "zh"},
        {"doc_id": "E1", "text": "war crisis disaster", "language": "en"},
    ])
    path = tmp_path / "双语 情感.csv"
    source.to_csv(path, index=False, encoding="utf-8")
    payload = {
        "dataPath": str(path),
        "fieldMapping": {"doc_id": "doc_id", "text": "text", "language": "language"},
        "cleanConfig": {
            "minTextLength": 1, "removeDuplicates": False,
            "zh": {"useDefaultStopwords": False}, "en": {"useDefaultStopwords": False},
        },
    }
    reset_state()
    zh = handle("task.sentiment", {**payload, "language": "zh"})
    en = handle("task.sentiment", {**payload, "language": "en"})
    assert zh["data"]["rows"][0]["sentiment"] == "positive"
    assert en["data"]["rows"][0]["sentiment"] == "negative"
    assert zh["state"]["workflow"]["sentimentDone"] is True
    assert set(get_state().sentiment_results) == {"zh", "en"}
    handle("task.clean", payload)
    assert get_state().sentiment_results == {}


def test_export_writes_sentiment_csv_and_session_config(tmp_path):
    source = tmp_path / "documents.csv"
    pd.DataFrame([
        {"doc_id": "E1", "text": "war crisis disaster", "language": "en", "genre": "news"},
        {"doc_id": "E2", "text": "peace hope prosperity", "language": "en", "genre": "editorial"},
    ]).to_csv(source, index=False, encoding="utf-8")
    output = tmp_path / "export"
    response = handle("task.export", {
        "dataPath": str(source), "outputDir": str(output), "exportLanguages": ["en"],
        "exportItems": ["sentiment_documents", "sentiment_summary", "session_config"],
        "fieldMapping": {"doc_id": "doc_id", "text": "text", "language": "language"},
        "cleanConfig": {"minTextLength": 1, "removeDuplicates": False, "en": {"useDefaultStopwords": False}},
        "sentimentConfigs": {"en": {"groupBy": "genre"}},
    })
    assert response["ok"] is True
    documents = output / "en" / "sentiment_documents.csv"
    assert documents.read_bytes().startswith(b"\xef\xbb\xbf")
    assert list(pd.read_csv(documents).columns) == [
        "doc_id", "sentiment", "sentiment_label", "score", "raw_score",
        "matched_words", "positive_hits", "negative_hits", "token_count",
        "positive_terms", "negative_terms",
    ]
    summary = output / "en" / "sentiment_summary.csv"
    assert list(pd.read_csv(summary).columns) == [
        "group", "documents", "positive", "neutral", "negative", "average_score"
    ]
    session = (output / "session_config.json").read_text(encoding="utf-8")
    assert '"sentimentConfigs"' in session
    assert '"sentimentCompletedLanguages": [' in session
