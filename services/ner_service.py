"""Deterministic bilingual named-entity recognition (v2.3).

命名实体识别采用"本地统计模型 + 历史词典 + 规则"的混合方案，识别人名、地名、机构、官职、时间五类实体：

- 中文使用 jieba.posseg 的 HMM 统计标注（nr/ns/nt/t）作为基础模型，叠加内置官职、年号种子词典与时间规则。
- 英文在未安装英文统计 NER 模型时使用大写专名规则 + 头衔/机构/地名关键词词典 + 时间规则，并在结果中显式说明所用引擎。
- 分析对象是清洗阶段保留的原始 `text` 字段，因此字符位置和上下文都能回溯到原文。
- 别名、异体字与简称保留原始值，聚合只合并完全相同的表面形式，不做不可逆归并。
- 重叠、重复与规则冲突按固定优先级（词典 > 规则 > 统计模型；再按跨度长度、起始位置）确定性裁决。
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Sequence, Tuple


LANGUAGE_LABELS = {"zh": "中文", "en": "英文"}

# 五类核心实体的稳定顺序与中文标签。
ENTITY_TYPES: Tuple[str, ...] = ("person", "location", "organization", "office", "time")
ENTITY_LABELS: Dict[str, str] = {
    "person": "人名", "location": "地名", "organization": "机构", "office": "官职", "time": "时间",
}
# 结果来源优先级：自定义/内置词典 > 规则 > 统计模型；数值越大越优先。
SOURCE_PRIORITY: Dict[str, int] = {"dictionary": 3, "rule": 2, "model": 1}

# jieba 词性到实体类型的映射（仅取五类关心的标签）。
JIEBA_FLAG_TYPES: Dict[str, str] = {
    "nr": "person", "nrfg": "person", "nrt": "person",
    "ns": "location", "nsf": "location",
    "nt": "organization",
    "t": "time",
}

# ── 内置历史词典种子（第一方精选事实性列表，可随包分发；用户词典在此之上扩充）──────────

# 中文官职（历代常见官名，作为规则/词典匹配的基础，用户可导入补充）。
ZH_OFFICE_SEED: Tuple[str, ...] = (
    "皇帝", "太上皇", "皇后", "太后", "亲王", "郡王", "丞相", "宰相", "太尉", "御史大夫",
    "尚书", "侍郎", "尚书令", "中书令", "侍中", "太师", "太傅", "太保", "大将军", "将军",
    "都督", "刺史", "太守", "知府", "知州", "知县", "县令", "巡抚", "总督", "布政使",
    "按察使", "提督", "总兵", "参将", "游击", "翰林", "学士", "大学士", "军机大臣", "总理",
    "总统", "主席", "委员长", "部长", "省长", "市长", "县长", "大使", "公使", "领事",
)
# 中文年号（选取常见且歧义较小者，用于时间规则；用户可补充）。
ZH_ERA_SEED: Tuple[str, ...] = (
    "贞观", "开元", "天宝", "永乐", "洪武", "康熙", "雍正", "乾隆", "嘉庆", "道光",
    "咸丰", "同治", "光绪", "宣统", "民国", "洪宪", "建安", "开皇", "武德", "崇祯",
)

# 英文头衔（专名规则里用于强化 person 判定，以及自身作为 office 命中）。
EN_OFFICE_SEED: Tuple[str, ...] = (
    "President", "Vice President", "Prime Minister", "Minister", "Chancellor", "Emperor",
    "Empress", "King", "Queen", "Prince", "Princess", "Duke", "Governor", "Mayor", "General",
    "Admiral", "Colonel", "Captain", "Ambassador", "Consul", "Senator", "Secretary", "Chairman",
)
# 英文机构关键词（末词命中则整段大写短语归为机构）。
EN_ORG_KEYWORDS: Tuple[str, ...] = (
    "Government", "Ministry", "Department", "Bureau", "Office", "Company", "Corporation",
    "Council", "Committee", "Commission", "Party", "Army", "Navy", "University", "College",
    "Institute", "Society", "Association", "Union", "Congress", "Parliament", "Senate", "Court",
)
# 英文地名关键词（末词命中则整段大写短语归为地名）。
EN_LOCATION_KEYWORDS: Tuple[str, ...] = (
    "City", "Town", "Village", "County", "Province", "State", "Kingdom", "Empire", "Republic",
    "Island", "Islands", "River", "Mountain", "Mountains", "Lake", "Sea", "Bay", "Valley",
)
# 英文常见月份，供时间规则使用。
EN_MONTHS: Tuple[str, ...] = (
    "January", "February", "March", "April", "May", "June", "July", "August",
    "September", "October", "November", "December",
)
# 英文头衔/连接虚词，出现在专名短语内部时不打断整体（如 King of England）。
EN_NAME_CONNECTORS = frozenset({"of", "the", "de", "van", "von", "del", "della", "da", "di", "and"})

# 中文时间正则：年号纪年、公元纪年、干支/农历日期等常见历史时间表达。
ZH_TIME_PATTERNS: Tuple[re.Pattern, ...] = (
    re.compile(r"(?:公元)?前?\s*\d{1,4}\s*年(?:\d{1,2}\s*月)?(?:\d{1,2}\s*[日号])?"),
    re.compile(r"[一二三四五六七八九十百零元廿卅]{1,6}年(?:[一二三四五六七八九十百零正腊冬]{1,3}月)?(?:[一二三四五六七八九十百零廿卅初]{1,4}[日号])?"),
)


def _zh_era_pattern(eras: Sequence[str]) -> Optional[re.Pattern]:
    """Build a 年号+纪年 pattern (e.g. 光绪三十年 / 民国十七年) from the active era list."""
    names = [re.escape(name) for name in sorted(set(eras), key=len, reverse=True) if name]
    if not names:
        return None
    return re.compile(
        r"(?:" + "|".join(names) + r")(?:元|[一二三四五六七八九十百零廿卅]{1,4}|\d{1,4})?\s*年?"
    )

# 英文时间正则：完整日期、月份+年份、单独四位年份、世纪。
EN_TIME_PATTERNS: Tuple[re.Pattern, ...] = (
    re.compile(r"\b(?:January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{1,2}(?:st|nd|rd|th)?,?\s*\d{3,4}\b"),
    re.compile(r"\b(?:January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{3,4}\b"),
    re.compile(r"\b\d{1,2}(?:st|nd|rd|th)?\s+(?:of\s+)?(?:January|February|March|April|May|June|July|August|September|October|November|December),?\s*\d{3,4}\b"),
    re.compile(r"\b\d{1,2}(?:st|nd|rd|th)?\s+century(?:\s+(?:BC|AD|BCE|CE))?\b", re.IGNORECASE),
    re.compile(r"\b(?:1[0-9]|20)\d{2}\s*(?:BC|AD|BCE|CE)?\b"),
)
# 英文专名短语：一个或多个首字母大写的词，允许内部连接虚词。
EN_PROPER_NOUN = re.compile(
    r"\b[A-Z][A-Za-z’'\-]*(?:\s+(?:of|the|de|van|von|del|della|da|di|and|[A-Z][A-Za-z’'\-]*))*\b"
)


class NERAnalysisError(ValueError):
    """Raised when NER parameters or the selected corpus are unusable."""


@dataclass(frozen=True)
class NEROptions:
    language: str = "zh"
    entity_types: Tuple[str, ...] = ENTITY_TYPES
    min_mention_count: int = 1
    context_window: int = 20
    use_model: bool = True
    person_words: Tuple[str, ...] = ()
    location_words: Tuple[str, ...] = ()
    organization_words: Tuple[str, ...] = ()
    office_words: Tuple[str, ...] = ()
    time_words: Tuple[str, ...] = ()

    def validate(self) -> None:
        if self.language not in LANGUAGE_LABELS:
            raise NERAnalysisError("language 必须是 zh 或 en")
        active = [item for item in self.entity_types if item in ENTITY_TYPES]
        if not active:
            raise NERAnalysisError("至少需要启用一种实体类型")
        if self.min_mention_count < 1:
            raise NERAnalysisError("最低出现次数必须大于等于 1")
        if not 0 <= self.context_window <= 200:
            raise NERAnalysisError("上下文窗口必须在 0 到 200 之间")

    def active_types(self) -> Tuple[str, ...]:
        return tuple(item for item in ENTITY_TYPES if item in self.entity_types)


@dataclass
class Gazetteer:
    """按实体类型组织的词典（内置种子 + 用户自定义），保留原始表面形式。"""
    by_type: Dict[str, List[str]]
    era_pattern: Optional[re.Pattern] = None

    def entries(self, entity_type: str) -> List[str]:
        return self.by_type.get(entity_type, [])


def _clean_words(words: Sequence[str]) -> List[str]:
    seen: Dict[str, None] = {}
    for word in words:
        text = str(word).strip()
        if text:
            seen.setdefault(text, None)
    return list(seen.keys())


def build_gazetteer(language: str, options: NEROptions) -> Gazetteer:
    """Merge built-in seed lists with user-supplied dictionaries per entity type."""
    by_type: Dict[str, List[str]] = {entity_type: [] for entity_type in ENTITY_TYPES}
    if language == "zh":
        by_type["office"].extend(ZH_OFFICE_SEED)
    else:
        by_type["office"].extend(EN_OFFICE_SEED)
    user = {
        "person": options.person_words,
        "location": options.location_words,
        "organization": options.organization_words,
        "office": options.office_words,
        "time": options.time_words,
    }
    for entity_type, extra in user.items():
        by_type[entity_type].extend(extra)
    # 长词优先，保证词典匹配时"国民政府"先于"政府"命中。
    for entity_type in by_type:
        by_type[entity_type] = sorted(_clean_words(by_type[entity_type]), key=len, reverse=True)
    era_pattern = _zh_era_pattern(list(ZH_ERA_SEED) + list(options.time_words)) if language == "zh" else None
    return Gazetteer(by_type=by_type, era_pattern=era_pattern)


def _add_span(spans: List[Dict[str, Any]], start: int, end: int, entity_type: str, source: str, text: str) -> None:
    surface = text[start:end]
    if not surface.strip():
        return
    spans.append({
        "start": start, "end": end, "type": entity_type, "source": source, "surface": surface,
        "priority": SOURCE_PRIORITY.get(source, 0),
    })


def _dictionary_spans(text: str, gazetteer: Gazetteer, active: Tuple[str, ...]) -> List[Dict[str, Any]]:
    spans: List[Dict[str, Any]] = []
    for entity_type in active:
        for word in gazetteer.entries(entity_type):
            start = text.find(word)
            while start != -1:
                _add_span(spans, start, start + len(word), entity_type, "dictionary", text)
                start = text.find(word, start + 1)
    return spans


def _time_spans(text: str, language: str, era_pattern: Optional[re.Pattern] = None) -> List[Dict[str, Any]]:
    spans: List[Dict[str, Any]] = []
    patterns = ZH_TIME_PATTERNS if language == "zh" else EN_TIME_PATTERNS
    for pattern in patterns:
        for match in pattern.finditer(text):
            _add_span(spans, match.start(), match.end(), "time", "rule", text)
    if era_pattern is not None:
        for match in era_pattern.finditer(text):
            if match.group(0).strip():
                _add_span(spans, match.start(), match.end(), "time", "rule", text)
    return spans


def _load_jieba_posseg():
    """Import jieba.posseg lazily; returns None when unavailable so the caller can degrade."""
    try:
        import jieba.posseg as pseg  # noqa: WPS433 - optional statistical backend
    except Exception:  # pragma: no cover - jieba is a hard dependency, guarded for safety
        return None
    return pseg


def _chinese_model_spans(text: str, active: Tuple[str, ...]) -> Tuple[List[Dict[str, Any]], bool]:
    """Tag Chinese entities with jieba's HMM POS tagger; second value marks model availability."""
    pseg = _load_jieba_posseg()
    if pseg is None:
        return [], False
    spans: List[Dict[str, Any]] = []
    cursor = 0
    for token in pseg.cut(text):
        word = token.word
        # jieba 保留原文所有字符（含空白/标点），据此在原文中定位。
        start = text.find(word, cursor)
        if start == -1:
            start = cursor
        end = start + len(word)
        cursor = end
        entity_type = JIEBA_FLAG_TYPES.get(token.flag)
        if entity_type and entity_type in active and word.strip():
            _add_span(spans, start, end, entity_type, "model", text)
    return spans, True


def _english_rule_spans(text: str, gazetteer: Gazetteer, active: Tuple[str, ...]) -> List[Dict[str, Any]]:
    """Recognise English entities from capitalised proper-noun phrases plus keyword gazetteers."""
    spans: List[Dict[str, Any]] = []
    office_lookup = {word.casefold() for word in gazetteer.entries("office")}
    org_keywords = {word.casefold() for word in EN_ORG_KEYWORDS}
    location_keywords = {word.casefold() for word in EN_LOCATION_KEYWORDS}
    for match in EN_PROPER_NOUN.finditer(text):
        phrase = match.group(0).strip()
        if not phrase:
            continue
        words = phrase.split()
        # 去掉短语首尾的连接虚词（of/the 等），保证跨度贴合实体本身。
        while words and words[0].casefold() in EN_NAME_CONNECTORS:
            words = words[1:]
        while words and words[-1].casefold() in EN_NAME_CONNECTORS:
            words = words[:-1]
        if not words:
            continue
        surface = " ".join(words)
        start = text.find(surface, match.start())
        if start == -1:
            continue
        end = start + len(surface)
        last = words[-1].casefold()
        head = words[0].casefold()
        if head in office_lookup and len(words) >= 2:
            # "President Lincoln" → 官职词单独成 office，其余大写词作为 person，二者不重叠。
            title_len = 0
            while title_len < len(words) - 1 and " ".join(w.casefold() for w in words[: title_len + 1]) in office_lookup:
                title_len += 1
            if title_len == 0:
                title_len = 1
            title_surface = " ".join(words[:title_len])
            name_surface = " ".join(words[title_len:])
            if "office" in active and title_surface:
                _add_span(spans, start, start + len(title_surface), "office", "dictionary", text)
            if name_surface and "person" in active:
                name_start = text.find(name_surface, start + len(title_surface))
                if name_start != -1:
                    _add_span(spans, name_start, name_start + len(name_surface), "person", "rule", text)
            continue
        if last in org_keywords:
            entity_type = "organization"
        elif last in location_keywords:
            entity_type = "location"
        elif surface.casefold() in office_lookup:
            entity_type = "office"
        else:
            entity_type = "person"  # 默认将独立大写专名视为人名，供人工复核
        if entity_type in active:
            _add_span(spans, start, end, entity_type, "rule", text)
    return spans


def _resolve_conflicts(spans: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Deterministically drop overlapping spans: keep highest priority, then longest, then leftmost."""
    ordered = sorted(
        spans,
        key=lambda span: (-span["priority"], -(span["end"] - span["start"]), span["start"], span["type"]),
    )
    kept: List[Dict[str, Any]] = []
    for span in ordered:
        if any(span["start"] < other["end"] and other["start"] < span["end"] for other in kept):
            continue
        kept.append(span)
    kept.sort(key=lambda span: (span["start"], span["end"]))
    return kept


def _context(text: str, start: int, end: int, window: int) -> str:
    left = max(0, start - window)
    right = min(len(text), end + window)
    prefix = "…" if left > 0 else ""
    suffix = "…" if right < len(text) else ""
    snippet = text[left:right].replace("\n", " ").replace("\r", " ").strip()
    return f"{prefix}{snippet}{suffix}"


def _extract_document(text: str, gazetteer: Gazetteer, options: NEROptions, active: Tuple[str, ...]) -> Tuple[List[Dict[str, Any]], bool]:
    """Run all recognisers on one document and return conflict-free spans + model availability."""
    spans: List[Dict[str, Any]] = []
    spans.extend(_dictionary_spans(text, gazetteer, active))
    if "time" in active:
        spans.extend(_time_spans(text, options.language, gazetteer.era_pattern))
    model_available = True
    if options.language == "zh":
        if options.use_model:
            model_spans, model_available = _chinese_model_spans(text, active)
            spans.extend(model_spans)
    else:
        spans.extend(_english_rule_spans(text, gazetteer, active))
    return _resolve_conflicts(spans), model_available


def analyze_ner(
    texts_by_document: Sequence[str],
    options: NEROptions,
    doc_ids: Optional[Sequence[Any]] = None,
) -> Dict[str, Any]:
    """Extract five entity types from one language corpus.

    Returns aggregated entities, per-mention rows with char offsets and context, and a summary.
    Recognition runs on the ORIGINAL text so positions and evidence trace back to the source.
    """
    options.validate()
    documents = [("" if text is None else str(text)) for text in texts_by_document]
    if not documents:
        raise NERAnalysisError(f"当前{LANGUAGE_LABELS[options.language]}没有已清洗文献")

    active = options.active_types()
    gazetteer = build_gazetteer(options.language, options)
    ids = list(doc_ids) if doc_ids is not None else [str(index + 1) for index in range(len(documents))]

    mentions: List[Dict[str, Any]] = []
    # 聚合键为 (类型, 表面形式)，只合并完全相同的原文，不做别名/异体归并。
    aggregate: Dict[Tuple[str, str], Dict[str, Any]] = {}
    order: List[Tuple[str, str]] = []
    model_available = True   # 统计模型后端是否可用（环境提示信号；en 恒为 True）
    model_used = False        # 是否真正运行了统计模型

    for index, text in enumerate(documents):
        doc_id = str(ids[index]) if index < len(ids) else str(index + 1)
        spans, doc_model_available = _extract_document(text, gazetteer, options, active)
        if options.language == "zh" and options.use_model:
            if doc_model_available:
                model_used = True
            else:
                model_available = False  # jieba 加载失败：环境不可用，需给出提示
        for span in spans:
            surface = span["surface"]
            entity_type = span["type"]
            mentions.append({
                "doc_id": doc_id,
                "entity": surface,
                "entity_type": entity_type,
                "entity_type_label": ENTITY_LABELS[entity_type],
                "start": span["start"],
                "end": span["end"],
                "source": span["source"],
                "context": _context(text, span["start"], span["end"], options.context_window),
            })
            key = (entity_type, surface)
            if key not in aggregate:
                aggregate[key] = {
                    "entity": surface, "entity_type": entity_type,
                    "entity_type_label": ENTITY_LABELS[entity_type],
                    "mention_count": 0, "_docs": set(), "sources": set(),
                }
                order.append(key)
            bucket = aggregate[key]
            bucket["mention_count"] += 1
            bucket["_docs"].add(doc_id)
            bucket["sources"].add(span["source"])

    entities: List[Dict[str, Any]] = []
    for key in order:
        bucket = aggregate[key]
        if bucket["mention_count"] < options.min_mention_count:
            continue
        entities.append({
            "entity": bucket["entity"],
            "entity_type": bucket["entity_type"],
            "entity_type_label": bucket["entity_type_label"],
            "mention_count": bucket["mention_count"],
            "document_count": len(bucket["_docs"]),
            "sources": "、".join(sorted(bucket["sources"])),
        })
    # 明细行也按最低出现次数过滤，保证明细与聚合口径一致。
    kept_entities = {(item["entity_type"], item["entity"]) for item in entities}
    mentions = [row for row in mentions if (row["entity_type"], row["entity"]) in kept_entities]

    # 稳定排序：出现次数降序、文档数降序、类型顺序、表面形式。
    type_rank = {entity_type: rank for rank, entity_type in enumerate(ENTITY_TYPES)}
    entities.sort(key=lambda item: (-item["mention_count"], -item["document_count"], type_rank[item["entity_type"]], item["entity"]))
    for rank, item in enumerate(entities, 1):
        item["rank"] = rank

    type_counts = {entity_type: 0 for entity_type in active}
    for item in entities:
        type_counts[item["entity_type"]] = type_counts.get(item["entity_type"], 0) + 1

    if options.language == "zh":
        if model_used:
            engine = "jieba.posseg 统计标注 + 历史词典 + 规则"
        elif not options.use_model:
            engine = "历史词典 + 规则（已禁用统计模型）"
        else:
            engine = "历史词典 + 规则（统计模型不可用）"
    else:
        engine = "大写专名规则 + 头衔/机构/地名词典 + 时间规则"

    summary = {
        "documents": len(documents),
        "entities": len(entities),
        "mentions": len(mentions),
        "typeCounts": type_counts,
        "modelAvailable": bool(model_available),
        "engine": engine,
    }
    return {
        "language": options.language,
        "engine": engine,
        "summary": summary,
        "entities": entities,
        "mentions": mentions,
        "typeChart": [
            {"type": entity_type, "label": ENTITY_LABELS[entity_type], "value": type_counts.get(entity_type, 0)}
            for entity_type in active
        ],
    }

