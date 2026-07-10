import json

import pandas as pd
import pytest

from backend.bridge import handle
from models.app_state import reset_state


def _run_in_fresh_bridge(command, payload):
    """模拟 Tauri 为每个任务启动一个新的 Python bridge 进程。"""
    reset_state()
    return handle(command, json.loads(json.dumps(payload)))


def test_bridge_downstream_task_requires_import_session():
    reset_state()

    with pytest.raises(ValueError, match="未找到已导入的真实文件"):
        handle("task.clean", {})


def test_bridge_rebuilds_real_file_workflow_from_session_payload(tmp_path):
    metadata_path = tmp_path / "metadata.csv"
    text_path = tmp_path / "text.csv"
    output_dir = tmp_path / "export"
    rows = [
        ("001", "市场与工厂", "申报", "1931-01-05", "市场 贸易 工厂 生产 经济 贸易"),
        ("002", "学校新制", "大公报", "1932-03-12", "学校 教育 学生 课程 教师 学习"),
        ("003", "城市交通", "申报", "1933-08-18", "城市 交通 道路 汽车 市政 出行"),
        ("004", "乡村建设", "民国日报", "1934-11-02", "乡村 建设 农民 水利 土地 农业"),
        ("005", "金融改革", "大公报", "1935-06-22", "金融 银行 货币 改革 资本 投资"),
        ("006", "公共卫生", "申报", "1936-09-09", "公共 卫生 医院 疾病 防疫 健康"),
    ]
    pd.DataFrame(
        [dict(doc_id=row[0], article_title=row[1], newspaper=row[2], pub_date=row[3]) for row in rows]
    ).to_csv(metadata_path, index=False, encoding="utf-8")
    pd.DataFrame([dict(doc_id=row[0], text=row[4]) for row in rows]).to_csv(text_path, index=False, encoding="utf-8")

    imported = _run_in_fresh_bridge("task.import", {
        "metadataPath": str(metadata_path),
        "textPath": str(text_path),
        "metadataIdField": "doc_id",
        "textIdField": "doc_id",
        "projectName": "真实文件回归测试",
    })
    assert imported["ok"]
    assert imported["data"]["mergedRows"] == len(rows)

    cleaned = _run_in_fresh_bridge("task.clean", {
        **imported["state"]["session"]["payload"],
        "options": {"minTextLength": 1, "minDocFreq": 1, "maxDocFreqRatio": 1.0},
    })
    assert cleaned["ok"]
    assert cleaned["data"]["documents"] == len(rows)

    lda = _run_in_fresh_bridge("task.lda", {
        **cleaned["state"]["session"]["payload"],
        "numTopics": 2,
        "passes": 1,
        "iterations": 10,
        "minDocFreq": 1,
        "maxDocFreqRatio": 1.0,
    })
    assert lda["ok"]
    assert lda["data"]["topicCount"] == 2

    exported = _run_in_fresh_bridge("task.export", {
        **lda["state"]["session"]["payload"],
        "outputDir": str(output_dir),
    })
    assert exported["ok"]
    assert exported["data"]["count"] >= 6
    assert (output_dir / "merged_data.csv").exists()
    assert (output_dir / "lda_doc_topic.csv").exists()

    session_config = json.loads((output_dir / "session_config.json").read_text(encoding="utf-8"))
    assert session_config["projectName"] == "真实文件回归测试"
    assert session_config["outputDir"] == str(output_dir)
    assert session_config["metadataPath"] == str(metadata_path)
    assert session_config["options"]["minTextLength"] == 1
    assert session_config["numTopics"] == 2
