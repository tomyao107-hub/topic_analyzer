"""针对稳健性修复的回归测试：CSV 读取、导出隔离、主题编号一致性。"""
import json

import pandas as pd
import pytest

import backend.bridge as bridge
import services.frequency_service as frequency_service
from backend.bridge import handle
from models.app_state import reset_state
from services.data_service import load_file


@pytest.fixture(autouse=True)
def _reset_state():
    reset_state()
    yield
    reset_state()


def test_empty_csv_raises_friendly_error(tmp_path):
    path = tmp_path / "empty.csv"
    path.write_text("", encoding="utf-8")
    with pytest.raises(ValueError, match="空|没有可解析"):
        load_file(str(path))


def test_missing_file_raises_friendly_error(tmp_path):
    with pytest.raises(ValueError, match="找不到文件"):
        load_file(str(tmp_path / "does_not_exist.csv"))


def test_lda_dominant_topic_uses_one_based_numbering():
    from services.lda_service import get_doc_topics

    class _FakeModel:
        num_topics = 3

        def get_document_topics(self, bow, minimum_probability=0.0):
            # 第 3 个主题（索引 2）概率最高
            return [(0, 0.1), (1, 0.2), (2, 0.7)]

    df = get_doc_topics(_FakeModel(), [["a"], ["b"]])
    # 索引 2 的主导主题应显示为“主题3”，与 STM 及前端卡片的 1 起始一致
    assert df["dominant_topic"].tolist() == ["主题3", "主题3"]


def test_export_word_frequency_survives_word_cloud_failure(tmp_path, monkeypatch):
    """缺少中文字体时词云失败，但词频 CSV 仍应成功导出。"""
    source = tmp_path / "documents.csv"
    pd.DataFrame([
        {"doc_id": "Z1", "text": "市场 贸易 市场", "language": "zh"},
        {"doc_id": "Z2", "text": "市场 工厂 贸易", "language": "zh"},
    ]).to_csv(source, index=False, encoding="utf-8")
    output = tmp_path / "export"

    def _boom(*_args, **_kwargs):
        raise frequency_service.FrequencyAnalysisError("未找到可用中文字体")

    monkeypatch.setattr(bridge, "render_word_cloud_png", _boom)

    response = handle("task.export", {
        "dataPath": str(source), "outputDir": str(output), "exportLanguages": ["zh"],
        "exportItems": ["word_frequency", "word_cloud"],
        "fieldMapping": {"doc_id": "doc_id", "text": "text", "language": "language"},
        "cleanConfig": {"minTextLength": 1, "removeDuplicates": False, "zh": {"useDefaultStopwords": False}},
        "frequencyConfigs": {"zh": {"topN": 20, "minTermFrequency": 1, "minDocumentFrequency": 1}},
    })

    assert response["ok"] is True
    assert (output / "zh" / "word_frequency.csv").exists()
    assert not (output / "zh" / "word_cloud.png").exists()
    error_keys = {error["key"] for error in response["data"]["errors"]}
    assert error_keys == {"word_cloud"}
    assert "zh/word_frequency.csv" in response["data"]["exported"]


def test_english_curly_apostrophe_contraction_survives_cleaning():
    """弯引号缩写（don't 的弯引号形式）不应在清洗时被拆坏。"""
    from services.clean_service import CleanOptions, tokenize_documents

    options = CleanOptions()
    options.min_text_length = 1
    tokens, _ = tokenize_documents(["I don’t know the workers’ rights"], ["en"], options, {"en": set()})
    # 弯引号被归一化为直引号并保留在词内；外围撇号（workers'）被裁剪
    assert "don't" in tokens[0]
    assert "workers" in tokens[0]
    assert "don" not in tokens[0]


def test_json_safe_removes_nan_and_infinity_and_numpy():
    import numpy as np

    payload = {
        "a": float("nan"),
        "b": float("inf"),
        "c": np.float64(1.5),
        "d": np.int64(7),
        "e": [float("nan"), "keep", np.float32(2.0)],
        "f": {"nested": float("-inf")},
    }
    safe = bridge._json_safe(payload)
    text = json.dumps(safe, allow_nan=False)  # 若残留 NaN/Inf 会抛错
    assert safe["a"] is None
    assert safe["b"] is None
    assert safe["c"] == 1.5
    assert safe["d"] == 7
    assert safe["e"][0] is None and safe["e"][1] == "keep"
    assert safe["f"]["nested"] is None
    assert "NaN" not in text and "Infinity" not in text


def test_compare_output_is_strict_json_when_metadata_has_blanks(tmp_path):
    """代表文章含空元数据（NaN）时，compare 主命令输出仍应是严格 JSON。"""
    source = tmp_path / "documents.csv"
    pd.DataFrame([
        {"doc_id": "Z1", "text": "市场 贸易 工厂 生产 商品 价格 贸易", "language": "zh",
         "source_name": "申报", "creator": "", "title": "甲"},
        {"doc_id": "Z2", "text": "学校 教育 学生 课程 教师 学习 学校", "language": "zh",
         "source_name": "大公报", "creator": "", "title": ""},
        {"doc_id": "Z3", "text": "乡村 建设 农民 合作 水利 土地 农业", "language": "zh",
         "source_name": "申报", "creator": "钱", "title": "丙"},
    ]).to_csv(source, index=False, encoding="utf-8")

    payload = {
        "dataPath": str(source),
        "fieldMapping": {"doc_id": "doc_id", "text": "text", "language": "language"},
        "language": "zh", "model": "lda", "axisField": "source_name",
        "numTopics": 2, "passes": 1, "iterations": 10, "minDocFreq": 1, "maxDocFreqRatio": 1.0,
        "cleanConfig": {"minTextLength": 1, "removeDuplicates": False, "zh": {"useDefaultStopwords": False}},
    }
    response = handle("task.compare", payload)
    assert response["ok"] is True
    # 严格 JSON：不接受裸 NaN/Infinity
    serialized = json.dumps(bridge._json_safe(response), allow_nan=False)
    assert "NaN" not in serialized


def test_export_languages_null_does_not_crash(tmp_path):
    """前端显式发送 exportLanguages=null 时，导出不应崩溃。"""
    source = tmp_path / "documents.csv"
    pd.DataFrame([
        {"doc_id": "Z1", "text": "市场 贸易 市场", "language": "zh"},
    ]).to_csv(source, index=False, encoding="utf-8")
    output = tmp_path / "export"
    response = handle("task.export", {
        "dataPath": str(source), "outputDir": str(output),
        "exportLanguages": None,
        "exportItems": ["documents"],
        "fieldMapping": {"doc_id": "doc_id", "text": "text", "language": "language"},
        "cleanConfig": {"minTextLength": 1, "removeDuplicates": False, "zh": {"useDefaultStopwords": False}},
    })
    assert response["ok"] is True
    assert (output / "documents.csv").exists()


def test_lda_coherence_export_json_has_no_bare_nan(tmp_path, monkeypatch):
    """coherence 计算失败（NaN）时导出的 lda_coherence.json 必须是合法 JSON。"""
    source = tmp_path / "documents.csv"
    pd.DataFrame([
        {"doc_id": "Z1", "text": "市场 贸易 工厂 生产 商品", "language": "zh"},
        {"doc_id": "Z2", "text": "学校 教育 学生 课程 教师", "language": "zh"},
    ]).to_csv(source, index=False, encoding="utf-8")
    output = tmp_path / "export"

    def fake_run_lda(payload):
        language = payload["language"]
        state = bridge.get_state()
        frame = state.cleaned_df[state.cleaned_df["language"] == language][["doc_id", "language"]].reset_index(drop=True)
        frame["topic_0"] = 1.0
        state.lda_results[language] = {
            "topics": [{"topic_id": 0, "words": [("市场", 1.0)]}],
            "doc_topics": frame,
            "coherence": float("nan"),
        }
        return {"language": language}

    monkeypatch.setattr(bridge, "_run_lda", fake_run_lda)
    response = handle("task.export", {
        "dataPath": str(source), "outputDir": str(output), "exportLanguages": ["zh"],
        "exportItems": ["lda_coherence"],
        "fieldMapping": {"doc_id": "doc_id", "text": "text", "language": "language"},
        "cleanConfig": {"minTextLength": 1, "removeDuplicates": False, "zh": {"useDefaultStopwords": False}},
    })
    assert response["ok"] is True
    coherence_file = output / "zh" / "lda_coherence.json"
    assert coherence_file.exists()
    # 用严格模式解析，裸 NaN 会抛错
    parsed = json.loads(coherence_file.read_text(encoding="utf-8"), parse_constant=_reject_constant)
    assert parsed["coherence_c_v"] is None


def _reject_constant(value):
    raise ValueError(f"非法 JSON 常量：{value}")


def test_pub_year_axis_sorts_numerically_not_lexically():
    """v1 GUI 使用 pub_year 作为横轴时应按数值排序，而非字符串排序。"""
    from services.compare_service import build_topic_summary

    frame = pd.DataFrame([
        {"pub_year": "1935", "topic_0": 0.5},
        {"pub_year": "1900", "topic_0": 0.1},
        {"pub_year": "1920", "topic_0": 0.3},
    ])
    summary = build_topic_summary(frame, "pub_year", ["topic_0"])
    # 数值排序：1900 < 1920 < 1935；且年份被转为整数
    assert summary["pub_year"].tolist() == [1900, 1920, 1935]


def test_pub_year_axis_drops_non_numeric_years():
    """非数字年份（如“民國二十四年”）在数值轴下被安全丢弃，不崩溃。"""
    from services.compare_service import build_topic_summary

    frame = pd.DataFrame([
        {"pub_year": "1935", "topic_0": 0.5},
        {"pub_year": "民國二十四年", "topic_0": 0.9},
    ])
    summary = build_topic_summary(frame, "pub_year", ["topic_0"])
    assert summary["pub_year"].tolist() == [1935]
