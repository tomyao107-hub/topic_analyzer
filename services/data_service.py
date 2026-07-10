"""
数据服务
负责文件读取、字段检测、表合并
"""
import os
from typing import Tuple, Optional, Dict
import pandas as pd

from utils.field_mapper import (
    META_FIELD_MAP, TEXT_FIELD_MAP,
    detect_columns, normalize_df, check_required_fields,
    parse_date_column, REQUIRED_META, REQUIRED_TEXT
)
from utils.logger import get_logger

logger = get_logger()


def _safe_sample(values, size: int = 3) -> list:
    """返回适合日志展示的首尾样本。"""
    cleaned = []
    for v in values:
        if pd.isna(v):
            cleaned.append("")
        else:
            cleaned.append(str(v).strip())
    return cleaned[:size]


def _log_dataframe_diagnostics(df: pd.DataFrame, path: str, source_desc: str):
    """记录 DataFrame 读取后的关键诊断信息，便于定位截断/读错表问题。"""
    filename = os.path.basename(path)
    logger.info(f"已加载{source_desc} {filename}：{len(df)} 行，{len(df.columns)} 列")
    logger.info(f"列名：{list(df.columns)}")

    if df.empty:
        logger.warning(f"文件 {filename} 读取结果为空表")
        return

    first_col = str(df.columns[0])
    first_head = _safe_sample(df.iloc[:3, 0].tolist())
    first_tail = _safe_sample(df.iloc[-3:, 0].tolist())
    logger.info(
        f"首列“{first_col}”样本：前3项={first_head}，后3项={first_tail}"
    )

    nonempty_rows = int(df.dropna(how="all").shape[0])
    logger.info(f"非全空行数：{nonempty_rows}")


def load_file(path: str) -> pd.DataFrame:
    """
    从 CSV 或 Excel 文件加载 DataFrame
    自动尝试多种编码
    """
    ext = os.path.splitext(path)[1].lower()
    if ext in (".xlsx", ".xls"):
        excel_file = pd.ExcelFile(path)
        sheet_names = excel_file.sheet_names
        logger.info(f"Excel 工作表：{sheet_names}")
        if not sheet_names:
            raise ValueError(f"Excel 文件中未找到工作表：{path}")

        df = pd.read_excel(excel_file, sheet_name=sheet_names[0], dtype=str)
        _log_dataframe_diagnostics(df, path, f"Excel工作表“{sheet_names[0]}”")
    elif ext == ".csv":
        for enc in ("utf-8-sig", "utf-8", "gbk", "gb18030", "big5"):
            try:
                df = pd.read_csv(path, dtype=str, encoding=enc)
                logger.info(f"以 {enc} 编码读取 {os.path.basename(path)}")
                _log_dataframe_diagnostics(df, path, f"CSV文件（编码 {enc}）")
                break
            except UnicodeDecodeError:
                continue
        else:
            raise ValueError(f"无法解码文件：{path}，请另存为 UTF-8 CSV")
    else:
        raise ValueError(f"不支持的文件格式：{ext}，请使用 .csv 或 .xlsx")

    # 去除列名首尾空白
    df.columns = [str(c).strip() for c in df.columns]
    return df


def detect_meta_columns(df: pd.DataFrame) -> Tuple[Dict[str, str], list, list]:
    """
    检测元数据表列名
    返回 (col_map, missing_required, unrecognized)
    """
    col_map, unrecognized = detect_columns(df, META_FIELD_MAP)
    missing = check_required_fields(col_map, REQUIRED_META)
    return col_map, missing, unrecognized


def detect_text_columns(df: pd.DataFrame) -> Tuple[Dict[str, str], list, list]:
    """
    检测文本表列名
    返回 (col_map, missing_required, unrecognized)
    """
    col_map, unrecognized = detect_columns(df, TEXT_FIELD_MAP)
    missing = check_required_fields(col_map, REQUIRED_TEXT)
    return col_map, missing, unrecognized


def merge_tables(
    meta_df: pd.DataFrame,
    text_df: pd.DataFrame,
    meta_col_map: Dict[str, str],
    text_col_map: Dict[str, str],
) -> Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """
    通过 doc_id 合并元数据表和文本表
    返回 (merged_df, unmatched_meta, unmatched_text)
    """
    # 标准化列名
    meta_norm = normalize_df(meta_df, meta_col_map)
    text_norm = normalize_df(text_df, text_col_map)

    # 确保 doc_id 为字符串
    meta_norm["doc_id"] = meta_norm["doc_id"].astype(str).str.strip()
    text_norm["doc_id"] = text_norm["doc_id"].astype(str).str.strip()

    # 内连接得到合并结果
    merged = pd.merge(meta_norm, text_norm, on="doc_id", how="inner")

    # 找出未匹配记录
    matched_ids = set(merged["doc_id"])
    unmatched_meta = meta_norm[~meta_norm["doc_id"].isin(matched_ids)].copy()
    unmatched_text = text_norm[~text_norm["doc_id"].isin(matched_ids)].copy()

    # 解析日期字段
    merged = parse_date_column(merged)

    logger.info(
        f"合并完成：匹配 {len(merged)} 篇，"
        f"元数据未匹配 {len(unmatched_meta)} 条，"
        f"文本未匹配 {len(unmatched_text)} 条"
    )

    return merged, unmatched_meta, unmatched_text
