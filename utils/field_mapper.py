"""
字段名映射工具
支持中英文列名自动识别与标准化
"""
from typing import Dict, Optional, Tuple
import pandas as pd

# ── v2 统一文献表字段 ──────────────────────────────────────────────────────────
DOCUMENT_FIELD_MAP = {
    "doc_id": ["doc_id", "文档编号", "文献编号", "docid", "id", "编号", "文章编号", "document_id"],
    "text": ["text", "正文文本", "正文", "content", "full_text", "文本", "内容", "article_text"],
    "language": ["language", "lang", "语言", "语种", "document_language"],
    "title": ["title", "题名", "标题", "文献题名", "article_title", "文章标题", "文题"],
    "creator": ["creator", "创建者", "作者/创建者", "author", "作者", "authors", "署名"],
    "date": ["date", "日期", "文献日期", "pub_date", "出版日期", "publication_date", "出版时间", "刊期"],
    "source_name": ["source_name", "来源", "来源名称", "newspaper", "报刊名", "报纸名", "刊名", "期刊名"],
    "source_type": ["source_type", "来源类型", "文献类型", "document_type"],
    "genre": ["genre", "文类", "体裁", "类别", "文章类别", "article_type", "type"],
    "place": ["place", "地点", "地名", "location"],
    "collection": ["collection", "汇集", "文集", "馆藏集", "collection_name"],
    "repository": ["repository", "收藏机构", "馆藏机构", "档案馆", "repository_name"],
    "volume": ["volume", "卷", "卷号", "vol"],
    "issue": ["issue", "期", "期号", "issue_no", "vol_issue", "卷期", "卷期号"],
    "page": ["page", "页码", "pages", "page_no", "页数"],
    "notes": ["notes", "备注", "note", "remarks"],
    "year": ["year", "年份", "日期年份", "pub_year", "出版年份", "出版年"],
    "month": ["month", "月份", "日期月份", "pub_month", "出版月份", "出版月"],
    "time_index": ["time_index", "时间序号", "连续月份", "月份序号", "month_index", "timeindex"],
}

DOCUMENT_FIELD_DISPLAY_NAMES = {
    "doc_id": "文献编号", "text": "正文文本", "language": "语言", "title": "题名",
    "creator": "作者/创建者", "date": "日期", "source_name": "来源",
    "source_type": "来源类型", "genre": "文类", "place": "地点",
    "collection": "文集/馆藏集", "repository": "收藏机构", "volume": "卷",
    "issue": "期", "page": "页码", "notes": "备注", "year": "年份",
    "month": "月份", "time_index": "时间序号",
}

REQUIRED_DOCUMENT = ["doc_id", "text", "language"]

# ── 标准字段名 ─────────────────────────────────────────────────────────────────
# 元数据表标准字段
META_FIELD_MAP = {
    # 文档编号
    "doc_id": ["doc_id", "文档编号", "docid", "id", "编号", "文章编号", "document_id"],
    # 报刊名
    "newspaper": ["newspaper", "报刊名", "报纸名", "刊名", "newspaper_name", "pub_name", "期刊名"],
    # 期号
    "issue_no": ["issue_no", "期号", "issue", "vol_issue", "卷期", "卷期号"],
    # 出版日期
    "pub_date": ["pub_date", "出版日期", "date", "publication_date", "日期", "出版时间", "刊期"],
    # 文章标题
    "article_title": ["article_title", "文章标题", "title", "标题", "文题"],
    # 作者
    "author": ["author", "作者", "authors", "署名"],
    # 页码
    "page": ["page", "页码", "pages", "page_no", "页数"],
    # 文类
    "genre": ["genre", "文类", "体裁", "类别", "文章类别", "article_type", "type"],
    # 可选扩展
    "column_name": ["column_name", "栏目名", "栏目", "column"],
    "column_class": ["column_class", "栏目类别", "column_type"],
    "notes": ["notes", "备注", "note", "remarks"],
    "pub_year": ["pub_year", "出版年份", "year", "年份", "出版年"],
    "pub_month": ["pub_month", "出版月份", "month", "月份", "出版月"],
    "time_index": ["time_index", "时间序号", "连续月份", "月份序号", "month_index", "timeindex"],
}

# 文本表标准字段
TEXT_FIELD_MAP = {
    "doc_id": ["doc_id", "文档编号", "docid", "id", "编号", "文章编号"],
    "text": ["text", "正文文本", "正文", "content", "full_text", "文本", "内容", "article_text"],
}

# 中文显示名
FIELD_DISPLAY_NAMES = {
    "doc_id": "文档编号",
    "newspaper": "报刊名",
    "issue_no": "期号",
    "pub_date": "出版日期",
    "article_title": "文章标题",
    "author": "作者",
    "page": "页码",
    "genre": "文类",
    "column_name": "栏目名",
    "column_class": "栏目类别",
    "notes": "备注",
    "pub_year": "出版年份",
    "pub_month": "出版月份",
    "time_index": "时间序号",
    "text": "正文文本",
}

# 必须字段
REQUIRED_META = ["doc_id"]
REQUIRED_TEXT = ["doc_id", "text"]


def detect_columns(df: pd.DataFrame, field_map: Dict) -> Tuple[Dict[str, str], list]:
    """
    自动检测 DataFrame 列名，返回 (映射字典, 未识别列列表)
    映射格式: {标准字段名: 原始列名}
    """
    col_map = {}
    unrecognized = []

    # 将 DataFrame 列名转小写去空格，便于匹配
    norm_cols = {col.lower().replace(" ", "").replace("_", ""): col
                 for col in df.columns}

    for std_name, aliases in field_map.items():
        found = False
        for alias in aliases:
            alias_norm = alias.lower().replace(" ", "").replace("_", "")
            if alias_norm in norm_cols:
                col_map[std_name] = norm_cols[alias_norm]
                found = True
                break
        # 如果未找到，该标准字段缺失（不加入 unrecognized，unrecognized 是指 df 中有但映射不到的列）

    # 找出 df 中未被识别的列
    mapped_originals = set(col_map.values())
    for col in df.columns:
        if col not in mapped_originals:
            unrecognized.append(col)

    return col_map, unrecognized


def normalize_df(df: pd.DataFrame, col_map: Dict[str, str]) -> pd.DataFrame:
    """
    按字段映射重命名 DataFrame，返回标准化后的副本
    """
    rename_dict = {v: k for k, v in col_map.items()}
    df_norm = df.rename(columns=rename_dict)
    return df_norm


def check_required_fields(col_map: Dict[str, str], required: list) -> list:
    """
    检查必须字段是否存在，返回缺失字段列表
    """
    missing = [f for f in required if f not in col_map]
    return missing


def _ensure_year_month_columns(df: pd.DataFrame) -> pd.DataFrame:
    if "pub_date" not in df.columns:
        return df
    parsed = pd.to_datetime(df["pub_date"], errors="coerce")
    if "pub_year" not in df.columns:
        df["pub_year"] = parsed.dt.year
    if "pub_month" not in df.columns:
        df["pub_month"] = parsed.dt.month
    return df


def add_time_index(df: pd.DataFrame) -> pd.DataFrame:
    """根据年月生成从 1 开始的连续月份序号。"""
    if "time_index" in df.columns:
        return df
    if "pub_year" not in df.columns or "pub_month" not in df.columns:
        return df

    years = pd.to_numeric(df["pub_year"], errors="coerce")
    months = pd.to_numeric(df["pub_month"], errors="coerce")
    valid = years.notna() & months.notna() & months.between(1, 12)
    df["time_index"] = pd.NA
    if not valid.any():
        return df

    month_numbers = years[valid].astype(int) * 12 + months[valid].astype(int)
    min_month_number = int(month_numbers.min())
    df.loc[valid, "time_index"] = (month_numbers - min_month_number + 1).astype("Int64")
    return df


def parse_date_column(df: pd.DataFrame) -> pd.DataFrame:
    """
    尝试解析 pub_date 列，并拆出 pub_year、pub_month、time_index。
    """
    df = df.copy()
    try:
        df = _ensure_year_month_columns(df)
        df = add_time_index(df)
    except Exception:
        pass

    return df


def parse_document_date(df: pd.DataFrame) -> pd.DataFrame:
    """解析 v2 文献日期，并在用户未提供时派生 year/month/time_index。"""
    df = df.copy()
    try:
        if "date" in df.columns:
            parsed = pd.to_datetime(df["date"], errors="coerce")
            if "year" not in df.columns:
                df["year"] = parsed.dt.year
            if "month" not in df.columns:
                df["month"] = parsed.dt.month
        if "time_index" not in df.columns and "year" in df.columns and "month" in df.columns:
            years = pd.to_numeric(df["year"], errors="coerce")
            months = pd.to_numeric(df["month"], errors="coerce")
            valid = years.notna() & months.notna() & months.between(1, 12)
            df["time_index"] = pd.NA
            if valid.any():
                month_numbers = years[valid].astype(int) * 12 + months[valid].astype(int)
                df.loc[valid, "time_index"] = (
                    month_numbers - int(month_numbers.min()) + 1
                ).astype("Int64")
    except Exception:
        pass
    return df


def get_display_name(std_field: str) -> str:
    return FIELD_DISPLAY_NAMES.get(std_field, std_field)
