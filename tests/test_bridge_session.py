import json

import pandas as pd
import pytest

from backend.bridge import handle
from models.app_state import reset_state


def _fresh(command, payload):
    reset_state()
    return handle(command, json.loads(json.dumps(payload)))


def _write_table(tmp_path):
    path = tmp_path / "documents.csv"
    pd.DataFrame([
        {"doc_id": "Z1", "text": "市场 贸易 工厂 生产", "language": "zh", "title": "甲", "source_name": "申报"},
        {"doc_id": "Z2", "text": "学校 教育 学生 课程", "language": "zh", "title": "乙", "source_name": "申报"},
        {"doc_id": "E1", "text": "markets factories workers production", "language": "en", "title": "A", "source_name": "Times"},
        {"doc_id": "E2", "text": "schools teachers students education", "language": "en", "title": "B", "source_name": "Times"},
    ]).to_csv(path, index=False, encoding="utf-8")
    return path


def test_downstream_task_requires_v2_data_path():
    with pytest.raises(ValueError, match="v2 文献表"):
        _fresh("task.clean", {})


def test_fresh_bridge_process_rebuilds_from_v2_session_payload(tmp_path):
    path = _write_table(tmp_path)
    payload = {
        "dataPath": str(path),
        "fieldMapping": {"doc_id": "doc_id", "text": "text", "language": "language"},
        "projectName": "可复现会话",
        "cleanConfig": {
            "minTextLength": 1, "removeDuplicates": False,
            "zh": {"useDefaultStopwords": False, "stopwords": []},
            "en": {"useDefaultStopwords": False, "stopwords": []},
        },
    }

    imported = _fresh("task.import", payload)
    assert imported["data"]["languageRows"] == {"zh": 2, "en": 2}
    cleaned = _fresh("task.clean", payload)
    assert cleaned["data"]["documents"] == 4
    assert cleaned["state"]["session"]["schemaVersion"] == 2
    assert cleaned["state"]["session"]["payload"]["dataPath"] == str(path)


def test_real_lda_runs_on_selected_language_only(tmp_path):
    path = _write_table(tmp_path)
    response = _fresh("task.lda", {
        "dataPath": str(path),
        "fieldMapping": {"doc_id": "doc_id", "text": "text", "language": "language"},
        "language": "en",
        "cleanConfig": {
            "minTextLength": 1, "removeDuplicates": False,
            "zh": {"useDefaultStopwords": False},
            "en": {"useDefaultStopwords": False},
        },
        "numTopics": 2,
        "passes": 1,
        "iterations": 10,
        "minDocFreq": 1,
        "maxDocFreqRatio": 1.0,
        "randomState": 7,
    })

    assert response["ok"] is True
    assert response["data"]["language"] == "en"
    assert response["data"]["topicCount"] == 2
    assert {row["language"] for row in response["data"]["documentTopics"]["rows"]} == {"en"}
