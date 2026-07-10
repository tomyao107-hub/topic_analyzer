import pandas as pd


def test_english_cleaning_repairs_linebreak_hyphen_and_preserves_inflection():
    from services.clean_service import CleanOptions, clean_text, tokenize_documents

    options = CleanOptions()
    options.min_text_length = 1
    text = "The inter-\nnational markets and workers' histories."
    tokens, _ = tokenize_documents([text], ["en"], options, {"en": {"the", "and"}})

    assert clean_text(text, options, "en").startswith("the international")
    assert "international" in tokens[0]
    assert "markets" in tokens[0]
    assert "market" not in tokens[0]


def test_chinese_minimum_token_length_one_keeps_historical_single_characters():
    from services.clean_service import CleanOptions, tokenize_documents

    options = CleanOptions()
    options.min_text_length = 1
    options.zh_min_token_length = 1
    tokens, _ = tokenize_documents(["国 与 民"], ["zh"], options, {"zh": {"与"}})
    assert tokens == [["国", "民"]]


def test_parse_document_date_builds_continuous_time_index_and_keeps_custom_fields():
    from utils.field_mapper import parse_document_date

    frame = pd.DataFrame([
        {"doc_id": "1", "date": "1920-03-01", "研究分组": "甲"},
        {"doc_id": "2", "date": "1920-04-01", "研究分组": "乙"},
        {"doc_id": "3", "date": "1921-03-01", "研究分组": "丙"},
    ])
    result = parse_document_date(frame)
    assert result["year"].tolist() == [1920, 1920, 1921]
    assert result["time_index"].astype(int).tolist() == [1, 2, 13]
    assert result["研究分组"].tolist() == ["甲", "乙", "丙"]


def test_compare_summary_supports_generic_historical_metadata():
    from services.compare_service import build_compare_summary

    frame = pd.DataFrame([
        {"source_type": "书信", "topic_0": 0.2},
        {"source_type": "书信", "topic_0": 0.4},
        {"source_type": "日记", "topic_0": 0.9},
    ])
    summary = build_compare_summary(frame, "source_type", ["topic_0"])
    rows = {row["source_type"]: row["topic_0"] for row in summary["rows"]}
    assert round(rows["书信"], 4) == 0.3
    assert round(rows["日记"], 4) == 0.9


def test_stm_formula_parser_supports_unicode_and_backticked_custom_columns():
    from services.stm_service import _extract_formula_variables

    assert _extract_formula_variables("~ 研究分组 + year") == ["研究分组", "year"]
    assert _extract_formula_variables("~ `archive collection` + s(year)") == ["archive collection", "year"]
