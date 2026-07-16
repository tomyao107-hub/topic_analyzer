import pandas as pd
import pytest

from backend.bridge import handle
from models.app_state import get_state, reset_state
from services.ner_service import (
    ENTITY_TYPES,
    NERAnalysisError,
    NEROptions,
    analyze_ner,
    build_gazetteer,
)


def test_chinese_model_extracts_five_entity_types():
    text = "民国十七年，蒋介石在南京国民政府任职。光绪三十年李鸿章任直隶总督。"
    result = analyze_ner([text], NEROptions(language="zh"), doc_ids=["Z1"])
    by_type = {(item["entity_type"], item["entity"]) for item in result["entities"]}
    assert ("person", "蒋介石") in by_type
    assert ("location", "南京") in by_type
    assert ("organization", "国民政府") in by_type
    assert ("office", "总督") in by_type  # 内置官职词典命中
    assert ("time", "民国十七年") in by_type  # 年号纪年时间规则
    assert result["summary"]["modelAvailable"] is True


def test_english_rules_split_title_and_name():
    text = "President Lincoln led the United States Government in July 1863."
    result = analyze_ner([text], NEROptions(language="en"), doc_ids=["E1"])
    by_type = {(item["entity_type"], item["entity"]) for item in result["entities"]}
    assert ("office", "President") in by_type       # 头衔单独成官职
    assert ("person", "Lincoln") in by_type          # 人名与头衔不重叠
    assert ("organization", "United States Government") in by_type
    assert ("time", "July 1863") in by_type


def test_mentions_carry_positions_and_context():
    text = "上海很繁华。"
    result = analyze_ner([text], NEROptions(language="zh", entity_types=("location",)), doc_ids=["Z1"])
    mention = next(row for row in result["mentions"] if row["entity"] == "上海")
    assert text[mention["start"]:mention["end"]] == "上海"  # 位置回溯到原文
    assert "上海" in mention["context"]
    assert mention["doc_id"] == "Z1"


def test_custom_dictionary_extends_results_with_priority():
    text = "此地名为泬邑，颇为古老。"
    baseline = analyze_ner([text], NEROptions(language="zh", entity_types=("person", "location")), doc_ids=["Z1"])
    assert not any(item["entity"] == "泬邑" for item in baseline["entities"])
    extended = analyze_ner(
        [text],
        NEROptions(language="zh", entity_types=("person", "location"), location_words=("泬邑",)),
        doc_ids=["Z1"],
    )
    hit = next(item for item in extended["entities"] if item["entity"] == "泬邑")
    assert hit["entity_type"] == "location"
    assert "dictionary" in hit["sources"]


def test_min_mention_count_filters_entities_and_mentions():
    docs = ["上海是城市。上海很大。", "北京见闻。"]
    result = analyze_ner(
        docs, NEROptions(language="zh", entity_types=("location",), min_mention_count=2), doc_ids=["A", "B"]
    )
    kept = {item["entity"] for item in result["entities"]}
    assert "上海" in kept and "北京" not in kept
    # 明细行与聚合口径一致，被过滤掉的实体不出现在 mentions 中
    assert all(row["entity"] == "上海" for row in result["mentions"])


def test_overlap_resolution_prefers_dictionary_over_model():
    # 内置官职"总督"与统计模型可能给出的跨度重叠时，词典优先且不产生重叠明细。
    result = analyze_ner(["直隶总督"], NEROptions(language="zh"), doc_ids=["Z1"])
    spans = sorted((row["start"], row["end"]) for row in result["mentions"])
    for (a_start, a_end), (b_start, b_end) in zip(spans, spans[1:]):
        assert a_end <= b_start  # 无重叠


def test_gazetteer_merges_seed_and_user_words():
    options = NEROptions(language="zh", office_words=("行走",))
    gazetteer = build_gazetteer("zh", options)
    assert "总督" in gazetteer.entries("office")  # 内置种子
    assert "行走" in gazetteer.entries("office")  # 用户扩充


def test_ner_rejects_empty_corpus_and_bad_options():
    with pytest.raises(NERAnalysisError, match="没有已清洗文献"):
        analyze_ner([], NEROptions(language="en"))
    with pytest.raises(NERAnalysisError, match="实体类型"):
        NEROptions(language="zh", entity_types=()).validate()
    with pytest.raises(NERAnalysisError, match="language"):
        NEROptions(language="fr").validate()


def test_disabling_model_falls_back_to_dictionary_rules():
    text = "光绪年间，李鸿章任直隶总督。"
    result = analyze_ner([text], NEROptions(language="zh", use_model=False), doc_ids=["Z1"])
    by_type = {(item["entity_type"], item["entity"]) for item in result["entities"]}
    assert ("office", "总督") in by_type   # 词典仍然命中
    # 环境可用但用户主动禁用统计模型：modelAvailable 仍为 True，引擎说明标注"已禁用"。
    assert result["summary"]["modelAvailable"] is True
    assert "已禁用统计模型" in result["engine"]
    # 未运行统计模型时不应出现 model 来源的实体。
    assert all("model" not in item["sources"] for item in result["entities"])


def test_bridge_ner_is_bilingual_and_reclean_invalidates_results(tmp_path):
    source = pd.DataFrame([
        {"doc_id": "Z1", "text": "蒋介石在南京国民政府任职。", "language": "zh"},
        {"doc_id": "E1", "text": "President Lincoln led the United States Government.", "language": "en"},
    ])
    path = tmp_path / "双语 实体.csv"
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
    zh = handle("task.ner", {**payload, "language": "zh"})
    en = handle("task.ner", {**payload, "language": "en"})
    zh_entities = {item["entity"] for item in zh["data"]["entities"]}
    en_entities = {item["entity"] for item in en["data"]["entities"]}
    assert "国民政府" in zh_entities
    assert "United States Government" in en_entities
    # 中英文互不污染
    assert not (zh_entities & en_entities)
    assert zh["state"]["workflow"]["nerDone"] is True
    assert set(get_state().ner_results) == {"zh", "en"}
    handle("task.clean", payload)
    assert get_state().ner_results == {}


def test_export_writes_ner_csv_and_session_config(tmp_path):
    source = tmp_path / "documents.csv"
    pd.DataFrame([
        {"doc_id": "E1", "text": "President Lincoln led the United States Government in July 1863.", "language": "en"},
    ]).to_csv(source, index=False, encoding="utf-8")
    output = tmp_path / "export"
    response = handle("task.export", {
        "dataPath": str(source), "outputDir": str(output), "exportLanguages": ["en"],
        "exportItems": ["entities", "entity_mentions", "session_config"],
        "fieldMapping": {"doc_id": "doc_id", "text": "text", "language": "language"},
        "cleanConfig": {"minTextLength": 1, "removeDuplicates": False, "en": {"useDefaultStopwords": False}},
    })
    assert response["ok"] is True
    entities = output / "en" / "entities.csv"
    assert entities.read_bytes().startswith(b"\xef\xbb\xbf")
    assert list(pd.read_csv(entities).columns) == [
        "rank", "entity", "entity_type", "entity_type_label",
        "mention_count", "document_count", "sources",
    ]
    mentions = output / "en" / "entity_mentions.csv"
    assert list(pd.read_csv(mentions).columns) == [
        "doc_id", "entity", "entity_type", "entity_type_label",
        "start", "end", "source", "context",
    ]
    session = (output / "session_config.json").read_text(encoding="utf-8")
    assert '"nerCompletedLanguages": [' in session


def test_entity_types_constant_is_stable():
    assert ENTITY_TYPES == ("person", "location", "organization", "office", "time")
