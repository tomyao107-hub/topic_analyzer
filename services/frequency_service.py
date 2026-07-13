"""Deterministic bilingual word-frequency analysis and word-cloud rendering."""
from __future__ import annotations

import io
import os
from collections import Counter
from dataclasses import dataclass
from typing import Dict, Iterable, Optional, Sequence


LANGUAGE_LABELS = {"zh": "中文", "en": "英文"}
SORT_FIELDS = {"term_frequency", "document_frequency"}


class FrequencyAnalysisError(ValueError):
    """Raised when frequency parameters or the selected corpus are unusable."""


@dataclass(frozen=True)
class FrequencyOptions:
    language: str = "zh"
    sort_by: str = "term_frequency"
    top_n: int = 50
    min_term_frequency: int = 1
    min_document_frequency: int = 1
    random_state: int = 42

    def validate(self) -> None:
        if self.language not in LANGUAGE_LABELS:
            raise FrequencyAnalysisError("language 必须是 zh 或 en")
        if self.sort_by not in SORT_FIELDS:
            raise FrequencyAnalysisError("sortBy 必须是 term_frequency 或 document_frequency")
        if not 1 <= self.top_n <= 500:
            raise FrequencyAnalysisError("Top N 必须在 1 到 500 之间")
        if self.min_term_frequency < 1:
            raise FrequencyAnalysisError("最低总词频必须大于等于 1")
        if self.min_document_frequency < 1:
            raise FrequencyAnalysisError("最低文档频率必须大于等于 1")


def analyze_word_frequency(tokens_by_document: Sequence[Sequence[str]], options: FrequencyOptions) -> Dict[str, object]:
    """Compute stable term/document frequencies for one language corpus."""
    options.validate()
    documents = [[str(token) for token in tokens if str(token)] for tokens in tokens_by_document]
    if not documents:
        raise FrequencyAnalysisError(f"当前{LANGUAGE_LABELS[options.language]}没有已清洗文献")

    term_counts: Counter[str] = Counter(token for tokens in documents for token in tokens)
    total_tokens = sum(term_counts.values())
    if total_tokens == 0:
        raise FrequencyAnalysisError(f"当前{LANGUAGE_LABELS[options.language]}清洗后没有有效词语")

    document_counts: Counter[str] = Counter()
    for tokens in documents:
        document_counts.update(set(tokens))

    rows = [
        {
            "word": word,
            "term_frequency": int(term_frequency),
            "document_frequency": int(document_counts[word]),
            "document_frequency_ratio": document_counts[word] / len(documents),
            "token_share": term_frequency / total_tokens,
        }
        for word, term_frequency in term_counts.items()
        if term_frequency >= options.min_term_frequency
        and document_counts[word] >= options.min_document_frequency
    ]
    if not rows:
        raise FrequencyAnalysisError("当前阈值过滤后没有词语，请降低最低总词频或最低文档频率")

    secondary = "document_frequency" if options.sort_by == "term_frequency" else "term_frequency"
    rows.sort(key=lambda row: (-int(row[options.sort_by]), -int(row[secondary]), str(row["word"])))
    selected = rows[: options.top_n]
    for rank, row in enumerate(selected, 1):
        row["rank"] = rank

    return {
        "language": options.language,
        "sortBy": options.sort_by,
        "documents": len(documents),
        "totalTokens": total_tokens,
        "uniqueWords": len(term_counts),
        "filteredWords": len(rows),
        "rows": selected,
    }


def find_cjk_font_path(extra_paths: Optional[Iterable[str]] = None) -> str:
    """Return a font file that can render Chinese, or an empty string."""
    candidates = [
        r"C:\Windows\Fonts\msyh.ttc",
        r"C:\Windows\Fonts\msyhbd.ttc",
        r"C:\Windows\Fonts\simhei.ttf",
        r"C:\Windows\Fonts\simsun.ttc",
    ]
    if extra_paths:
        candidates = [*extra_paths, *candidates]
    for path in candidates:
        if path and os.path.isfile(path):
            return os.path.abspath(path)
    try:
        from matplotlib import font_manager

        names = {
            "Microsoft YaHei", "SimHei", "SimSun", "Noto Sans CJK SC",
            "Source Han Sans SC", "WenQuanYi Micro Hei", "PingFang SC",
        }
        for entry in font_manager.fontManager.ttflist:
            if entry.name in names and os.path.isfile(entry.fname):
                return os.path.abspath(entry.fname)
    except Exception:
        return ""
    return ""


def render_word_cloud_png(
    rows: Sequence[Dict[str, object]], language: str, random_state: int = 42,
    font_path: Optional[str] = None, width: int = 1200, height: int = 720,
) -> bytes:
    """Render the displayed rows to a deterministic PNG using term frequency."""
    frequencies = {
        str(row["word"]): int(row["term_frequency"])
        for row in rows if row.get("word") and int(row.get("term_frequency", 0)) > 0
    }
    if not frequencies:
        raise FrequencyAnalysisError("没有可用于生成词云的词频结果")
    if language == "zh":
        font_path = font_path or find_cjk_font_path()
        if not font_path:
            raise FrequencyAnalysisError("未找到可用中文字体，无法生成中文词云；请安装微软雅黑、黑体或 Noto Sans CJK SC")
    try:
        from wordcloud import WordCloud
    except ImportError as exc:
        raise RuntimeError("缺少 wordcloud 依赖，请安装 requirements.txt 后重试") from exc

    cloud = WordCloud(
        width=width, height=height, background_color="white", font_path=font_path,
        random_state=random_state, collocations=False, prefer_horizontal=0.9,
    ).generate_from_frequencies(frequencies)
    buffer = io.BytesIO()
    cloud.to_image().save(buffer, format="PNG")
    return buffer.getvalue()
