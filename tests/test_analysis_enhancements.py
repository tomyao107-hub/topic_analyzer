import pandas as pd


def test_build_cleaned_records_keeps_metadata_text_and_tokens():
    from gui.pages.clean_page import build_cleaned_records
    from services.clean_service import CleanOptions

    merged = pd.DataFrame([
        {"doc_id": "1", "genre": "新闻", "text": "一二三，测试文本。"},
        {"doc_id": "2", "genre": "评论", "text": "第二篇文本。"},
    ])
    tokens = [["测试", "文本"], ["第二", "文本"]]
    opts = CleanOptions()
    opts.remove_numbers = True
    opts.remove_punct = True

    result = build_cleaned_records(merged, tokens, opts)

    assert list(result["doc_id"]) == ["1", "2"]
    assert list(result["genre"]) == ["新闻", "评论"]
    assert "cleaned_text" in result.columns
    assert list(result["tokens"]) == ["测试 文本", "第二 文本"]
    assert list(result["token_count"]) == [2, 2]


def test_filter_docs_by_genre_returns_matching_rows_and_tokens():
    from gui.pages.lda_page import filter_docs_by_genre

    df = pd.DataFrame([
        {"doc_id": "1", "genre": "新闻"},
        {"doc_id": "2", "genre": "评论"},
        {"doc_id": "3", "genre": "新闻"},
    ])
    tokens = [["a"], ["b"], ["c"]]

    filtered_df, filtered_tokens = filter_docs_by_genre(df, tokens, "新闻")

    assert list(filtered_df["doc_id"]) == ["1", "3"]
    assert filtered_tokens == [["a"], ["c"]]


def test_build_topic_summary_groups_axis_and_topics():
    from gui.pages.compare_page import build_topic_summary

    df = pd.DataFrame([
        {"genre": "新闻", "topic_0": 0.2, "topic_1": 0.8},
        {"genre": "新闻", "topic_0": 0.4, "topic_1": 0.6},
        {"genre": "评论", "topic_0": 0.9, "topic_1": 0.1},
    ])

    summary = build_topic_summary(df, "genre", ["topic_0", "topic_1"])

    assert list(summary["genre"]) == ["评论", "新闻"]
    assert round(float(summary.loc[summary["genre"] == "新闻", "topic_0"].iloc[0]), 4) == 0.3
    assert round(float(summary.loc[summary["genre"] == "评论", "topic_1"].iloc[0]), 4) == 0.1


def test_parse_date_column_builds_continuous_time_index():
    from utils.field_mapper import parse_date_column

    df = pd.DataFrame([
        {"doc_id": "1", "pub_year": "1920", "pub_month": "3"},
        {"doc_id": "2", "pub_year": "1920", "pub_month": "4"},
        {"doc_id": "3", "pub_year": "1921", "pub_month": "3"},
        {"doc_id": "4", "pub_year": "", "pub_month": ""},
    ])

    result = parse_date_column(df)

    assert list(result["time_index"].dropna().astype(int)) == [1, 2, 13]


def test_parse_date_column_keeps_existing_time_index():
    from utils.field_mapper import parse_date_column

    df = pd.DataFrame([
        {"doc_id": "1", "pub_year": "1920", "pub_month": "3", "time_index": "99"},
    ])

    result = parse_date_column(df)

    assert list(result["time_index"]) == ["99"]
