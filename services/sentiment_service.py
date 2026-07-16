"""Deterministic bilingual dictionary-and-rule sentiment analysis.

情感分析采用透明、可复现的词典与规则方法：命中情感词赋权，前置的否定词翻转极性，
程度副词按倍率缩放，文献得分归一化到 [-1, 1] 后再按阈值分类为正面/中性/负面。
中文与英文使用彼此独立的情感资源，词表随包分发（见 data/sentiment/NOTICE.md）。
"""
from __future__ import annotations

import os
import sys
from dataclasses import dataclass, field
from typing import Any, Dict, List, Mapping, Optional, Sequence


LANGUAGE_LABELS = {"zh": "中文", "en": "英文"}

# 程度副词倍率（内置精选表，未直接分发第三方程度副词文件）。
ZH_BOOSTERS: Dict[str, float] = {
    "最": 2.0, "极": 2.0, "极其": 2.0, "极为": 2.0, "无比": 2.0, "万分": 2.0, "十二分": 2.0,
    "非常": 1.6, "十分": 1.6, "格外": 1.6, "分外": 1.6, "太": 1.6, "尤其": 1.6, "异常": 1.6,
    "特别": 1.6, "超": 1.6, "超级": 1.6, "相当": 1.5, "颇": 1.5, "甚": 1.5,
    "很": 1.3, "挺": 1.3, "蛮": 1.3, "较": 1.2, "比较": 1.2, "更": 1.3, "更加": 1.4, "越发": 1.4,
    "稍": 0.6, "稍微": 0.6, "稍稍": 0.6, "有点": 0.6, "有些": 0.6, "略": 0.6, "略微": 0.6,
    "些许": 0.5, "多少": 0.7, "还": 0.8,
}
EN_BOOSTERS: Dict[str, float] = {
    "absolutely": 1.6, "completely": 1.6, "extremely": 1.8, "incredibly": 1.7, "totally": 1.6,
    "utterly": 1.7, "very": 1.4, "so": 1.3, "really": 1.4, "remarkably": 1.5, "especially": 1.4,
    "exceptionally": 1.6, "particularly": 1.4, "highly": 1.5, "hugely": 1.6, "super": 1.5,
    "greatly": 1.5, "deeply": 1.5, "truly": 1.4, "quite": 1.2, "rather": 1.2, "fairly": 1.1,
    "barely": 0.5, "slightly": 0.5, "somewhat": 0.6, "marginally": 0.5, "partly": 0.7, "less": 0.6,
}
EN_NEGATIONS = frozenset({
    "not", "no", "never", "none", "nobody", "nothing", "neither", "nor", "without", "cannot",
    "cant", "won't", "wont", "don't", "dont", "doesn't", "doesnt", "didn't", "didnt", "isn't",
    "isnt", "aren't", "arent", "wasn't", "wasnt", "weren't", "werent", "ain't", "hardly",
    "scarcely", "lack", "lacks", "lacking", "n't",
})

# 数据文件缺失时的兜底种子表，保证情感分析永不静默失效（与仓库“内置默认资源”的约定一致）。
ZH_SEED_POSITIVE = ("好", "优秀", "喜欢", "成功", "美好", "赞成", "支持", "进步", "繁荣", "和平", "希望", "光明")
ZH_SEED_NEGATIVE = ("坏", "失败", "讨厌", "痛苦", "灾难", "反对", "衰败", "混乱", "危机", "黑暗", "绝望", "腐败")
ZH_SEED_NEGATION = ("不", "没", "没有", "无", "非", "未", "别", "莫", "毫无", "并非")
EN_SEED_POSITIVE = ("good", "great", "excellent", "happy", "success", "peace", "hope", "progress", "prosperity", "victory")
EN_SEED_NEGATIVE = ("bad", "terrible", "awful", "sad", "failure", "war", "crisis", "poverty", "defeat", "disaster")


class SentimentAnalysisError(ValueError):
    """Raised when sentiment parameters or the selected corpus are unusable."""


def _resource_path(*parts: str) -> str:
    """Locate a bundled data file in both dev and frozen (PyInstaller) layouts."""
    base = getattr(sys, "_MEIPASS", None)
    if base:
        candidate = os.path.join(base, "data", "sentiment", *parts)
        if os.path.isfile(candidate):
            return candidate
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(root, "data", "sentiment", *parts)


@dataclass(frozen=True)
class SentimentOptions:
    language: str = "zh"
    positive_threshold: float = 0.05
    negative_threshold: float = -0.05
    use_negation: bool = True
    use_degree: bool = True
    top_evidence: int = 8
    group_by: str = ""
    positive_words: tuple = ()
    negative_words: tuple = ()

    def validate(self) -> None:
        if self.language not in LANGUAGE_LABELS:
            raise SentimentAnalysisError("language 必须是 zh 或 en")
        if not -1.0 <= self.negative_threshold <= self.positive_threshold <= 1.0:
            raise SentimentAnalysisError("阈值必须满足 -1 ≤ 负面阈值 ≤ 正面阈值 ≤ 1")
        if self.top_evidence < 1:
            raise SentimentAnalysisError("证据词数量必须大于等于 1")


@dataclass
class SentimentLexicon:
    language: str
    scores: Dict[str, float]
    negations: frozenset
    boosters: Mapping[str, float]

    def polarity(self, word: str) -> float:
        return self.scores.get(word, 0.0)


def _read_word_list(path: str) -> List[str]:
    if not os.path.isfile(path):
        return []
    with open(path, "r", encoding="utf-8") as handle:
        return [line.strip() for line in handle if line.strip()]


def _load_vader_scores(path: str) -> Dict[str, float]:
    scores: Dict[str, float] = {}
    if not os.path.isfile(path):
        return scores
    with open(path, "r", encoding="utf-8") as handle:
        for line in handle:
            parts = line.rstrip("\n").split("\t")
            if len(parts) < 2:
                continue
            word = parts[0].strip()
            try:
                measure = float(parts[1])
            except ValueError:
                continue
            if word:
                # normalise VADER's [-4, 4] valence into a unit-scale weight
                scores[word.casefold()] = max(-1.0, min(1.0, measure / 4.0))
    return scores


def load_lexicon(language: str, extra_positive: Sequence[str] = (), extra_negative: Sequence[str] = ()) -> SentimentLexicon:
    """Build a language lexicon from bundled data files with an inline fallback."""
    if language not in LANGUAGE_LABELS:
        raise SentimentAnalysisError("language 必须是 zh 或 en")
    scores: Dict[str, float] = {}
    if language == "en":
        scores.update(_load_vader_scores(_resource_path("en", "vader_lexicon.txt")))
        if not scores:
            scores.update({word: 1.0 for word in EN_SEED_POSITIVE})
            scores.update({word: -1.0 for word in EN_SEED_NEGATIVE})
        negations = EN_NEGATIONS
        boosters: Mapping[str, float] = EN_BOOSTERS
        normalise = str.casefold
    else:
        positive = _read_word_list(_resource_path("zh", "positive.txt")) or list(ZH_SEED_POSITIVE)
        negative = _read_word_list(_resource_path("zh", "negative.txt")) or list(ZH_SEED_NEGATIVE)
        for word in positive:
            scores[word] = 1.0
        for word in negative:
            scores[word] = -1.0
        loaded_negations = _read_word_list(_resource_path("zh", "negation.txt")) or list(ZH_SEED_NEGATION)
        negations = frozenset(loaded_negations)
        boosters = ZH_BOOSTERS
        normalise = lambda word: word  # noqa: E731 - identity for Chinese tokens

    for word in extra_positive:
        cleaned = normalise(str(word).strip())
        if cleaned:
            scores[cleaned] = 1.0
    for word in extra_negative:
        cleaned = normalise(str(word).strip())
        if cleaned:
            scores[cleaned] = -1.0
    return SentimentLexicon(language=language, scores=scores, negations=negations, boosters=boosters)


def _normalise_tokens(tokens: Sequence[str], language: str) -> List[str]:
    if language == "en":
        return [str(token).strip().casefold() for token in tokens if str(token).strip()]
    return [str(token).strip() for token in tokens if str(token).strip()]


def _score_document(tokens: Sequence[str], lexicon: SentimentLexicon, options: SentimentOptions) -> Dict[str, Any]:
    """Score one document; returns raw sum, hit counts and evidence terms."""
    words = _normalise_tokens(tokens, lexicon.language)
    raw = 0.0
    positive_hits = 0
    negative_hits = 0
    matched = 0
    positive_terms: List[str] = []
    negative_terms: List[str] = []
    window = 3  # look back this many tokens for negation / degree modifiers
    for index, word in enumerate(words):
        polarity = lexicon.polarity(word)
        if polarity == 0.0:
            continue
        weight = 1.0
        negate = False
        if options.use_negation or options.use_degree:
            start = max(0, index - window)
            # scan backwards; stop at the previous sentiment word so a modifier
            # only affects the nearest polarity term (avoids over-negation).
            for offset in range(index - 1, start - 1, -1):
                prior = words[offset]
                if lexicon.polarity(prior) != 0.0:
                    break
                if options.use_negation and prior in lexicon.negations:
                    negate = not negate
                elif options.use_degree and prior in lexicon.boosters:
                    weight *= lexicon.boosters[prior]
        value = polarity * weight
        if negate:
            value = -value
        raw += value
        matched += 1
        display = word
        if value > 0:
            positive_hits += 1
            if len(positive_terms) < options.top_evidence:
                positive_terms.append(display)
        elif value < 0:
            negative_hits += 1
            if len(negative_terms) < options.top_evidence:
                negative_terms.append(display)
    length = max(len(words), 1)
    # squashing keeps the document score inside [-1, 1] regardless of length
    score = raw / (length ** 0.5) if raw else 0.0
    score = max(-1.0, min(1.0, score))
    return {
        "raw": raw,
        "score": score,
        "matched": matched,
        "tokens": len(words),
        "positiveHits": positive_hits,
        "negativeHits": negative_hits,
        "positiveTerms": positive_terms,
        "negativeTerms": negative_terms,
    }


def _classify(score: float, options: SentimentOptions) -> str:
    if score >= options.positive_threshold:
        return "positive"
    if score <= options.negative_threshold:
        return "negative"
    return "neutral"


LABEL_TEXT = {"positive": "正面", "neutral": "中性", "negative": "负面"}


def analyze_sentiment(
    tokens_by_document: Sequence[Sequence[str]],
    options: SentimentOptions,
    doc_ids: Optional[Sequence[Any]] = None,
    metadata: Optional[Sequence[Mapping[str, Any]]] = None,
) -> Dict[str, Any]:
    """Score one language corpus; return per-document rows, distribution and aggregation."""
    options.validate()
    documents = [list(tokens) for tokens in tokens_by_document]
    if not documents:
        raise SentimentAnalysisError(f"当前{LANGUAGE_LABELS[options.language]}没有已清洗文献")

    lexicon = load_lexicon(options.language, options.positive_words, options.negative_words)
    if not lexicon.scores:
        raise SentimentAnalysisError(f"未能加载{LANGUAGE_LABELS[options.language]}情感词典")

    ids = list(doc_ids) if doc_ids is not None else [str(index + 1) for index in range(len(documents))]
    meta = list(metadata) if metadata is not None else [{} for _ in documents]

    rows: List[Dict[str, Any]] = []
    distribution = {"positive": 0, "neutral": 0, "negative": 0}
    total_matched = 0
    for index, tokens in enumerate(documents):
        scored = _score_document(tokens, lexicon, options)
        label = _classify(scored["score"], options)
        distribution[label] += 1
        total_matched += scored["matched"]
        rows.append({
            "doc_id": str(ids[index]) if index < len(ids) else str(index + 1),
            "sentiment": label,
            "sentiment_label": LABEL_TEXT[label],
            "score": round(scored["score"], 6),
            "raw_score": round(scored["raw"], 6),
            "matched_words": scored["matched"],
            "positive_hits": scored["positiveHits"],
            "negative_hits": scored["negativeHits"],
            "token_count": scored["tokens"],
            "positive_terms": "、".join(scored["positiveTerms"]),
            "negative_terms": "、".join(scored["negativeTerms"]),
        })

    scores = [row["score"] for row in rows]
    summary = {
        "documents": len(rows),
        "distribution": distribution,
        "averageScore": round(sum(scores) / len(scores), 6) if scores else 0.0,
        "matchedWords": total_matched,
        "lexiconSize": len(lexicon.scores),
    }

    aggregation: List[Dict[str, Any]] = []
    field_name = str(options.group_by or "").strip()
    if field_name:
        groups: Dict[str, Dict[str, Any]] = {}
        order: List[str] = []
        for index, row in enumerate(rows):
            raw_value = meta[index].get(field_name) if index < len(meta) else None
            key = "" if raw_value is None else str(raw_value).strip()
            if key == "" or key.lower() == "nan":
                key = "（缺失）"
            if key not in groups:
                groups[key] = {"group": key, "documents": 0, "positive": 0, "neutral": 0, "negative": 0, "_sum": 0.0}
                order.append(key)
            bucket = groups[key]
            bucket["documents"] += 1
            bucket[row["sentiment"]] += 1
            bucket["_sum"] += row["score"]
        for key in order:
            bucket = groups[key]
            count = max(bucket["documents"], 1)
            aggregation.append({
                "group": bucket["group"],
                "documents": bucket["documents"],
                "positive": bucket["positive"],
                "neutral": bucket["neutral"],
                "negative": bucket["negative"],
                "average_score": round(bucket["_sum"] / count, 6),
            })

    return {
        "language": options.language,
        "groupBy": field_name,
        "summary": summary,
        "rows": rows,
        "aggregation": aggregation,
    }
