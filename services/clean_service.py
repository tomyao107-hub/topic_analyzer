"""语言感知的历史文献清洗与分词服务。"""
import re
import unicodedata
from typing import Dict, List, Optional, Set, Tuple

from utils.logger import get_logger

logger = get_logger()

NOISE_PATTERN = re.compile(r"[□■◆◇▲△○●◎①②③④⑤⑥⑦⑧⑨⑩]")
PUNCT_PATTERN = re.compile(
    r'''[，。！？、；：“”‘’（）《》【】—…·「」『』〔〕〖〗,\.!?;:"'()\[\]{}_@#$%^&*+=<>/\\|~`]'''
)
NUMBER_PATTERN = re.compile(r"\d+")
# 英文标点清洗：故意不含撇号（' 及弯引号 ‘’），以便 don't / workers' 等
# 词内撇号存活到分词阶段，由 _tokenize_english 统一归一化并裁剪外围撇号。
ENGLISH_PUNCT_PATTERN = re.compile(
    r'''[，。！？、；：“”（）《》【】—…·「」『』〔〕〖〗,\.!?;:"()\[\]{}_@#$%^&*+=<>/\\|~`]'''
)
ENGLISH_LINEBREAK_HYPHEN = re.compile(r"(?<=[A-Za-zÀ-ÖØ-öø-ÿ])-\s*\r?\n\s*(?=[A-Za-zÀ-ÖØ-öø-ÿ])")
UNICODE_WORD_PATTERN = re.compile(r"[^\W\d_]+(?:[-'’][^\W\d_]+)*", re.UNICODE)


class CleanOptions:
    """通用与分语言清洗选项。"""

    def __init__(self):
        self.remove_empty = True
        self.remove_duplicates = True
        self.ocr_clean = True
        self.remove_punct = True
        self.remove_numbers = True
        self.traditional_to_simplified = False
        self.lowercase_english = True
        self.repair_english_hyphenation = True
        self.min_text_length = 10
        self.min_token_freq = 1
        self.min_doc_freq = 2
        self.max_doc_freq_ratio = 0.95
        self.zh_min_token_length = 1
        self.en_min_token_length = 2


def _is_latin_token(token: str) -> bool:
    letters = [char for char in token if char.isalpha()]
    return bool(letters) and all("LATIN" in unicodedata.name(char, "") for char in letters)


def clean_text(text: str, opts: CleanOptions, language: str = "zh") -> str:
    """清洗单篇文献；原始文本由调用方保留。"""
    if not isinstance(text, str):
        return ""

    result = unicodedata.normalize("NFKC", text)
    if language == "en" and opts.repair_english_hyphenation:
        result = ENGLISH_LINEBREAK_HYPHEN.sub("", result)
    if language == "en" and opts.lowercase_english:
        result = result.casefold()
    if opts.ocr_clean:
        result = NOISE_PATTERN.sub(" ", result)

    if language == "zh" and opts.traditional_to_simplified:
        try:
            import opencc
            result = opencc.OpenCC("t2s.json").convert(result)
        except ImportError:
            logger.warning("opencc 未安装，跳过繁简转换")

    if opts.remove_punct:
        # 英文分词需要先保留词内撇号和连字符；外围符号会在 token 提取时丢弃。
        if language == "zh":
            result = PUNCT_PATTERN.sub(" ", result)
        else:
            result = ENGLISH_PUNCT_PATTERN.sub(" ", result)
    if opts.remove_numbers:
        result = NUMBER_PATTERN.sub(" ", result)
    return re.sub(r"\s+", " ", result).strip()


def _tokenize_chinese(text: str, min_length: int) -> List[str]:
    try:
        import jieba
    except ImportError as exc:
        raise ImportError("jieba 未安装，请运行：pip install jieba") from exc
    return [word.strip() for word in jieba.cut(text, cut_all=False) if len(word.strip()) >= min_length]


def _tokenize_english(text: str, min_length: int) -> List[str]:
    words = []
    for match in UNICODE_WORD_PATTERN.finditer(text):
        word = match.group(0).replace("’", "'").strip("-'")
        letter_count = sum(char.isalpha() for char in word)
        if letter_count >= min_length and _is_latin_token(word):
            words.append(word)
    return words


def tokenize_documents(
    texts: List[str],
    languages: List[str],
    opts: CleanOptions,
    stopwords_by_language: Dict[str, Set[str]],
    custom_dict_path: Optional[str] = None,
) -> Tuple[List[List[str]], dict]:
    """按每行声明的语言分词，并保持与输入行严格对齐。"""
    if len(texts) != len(languages):
        raise ValueError("正文与语言列行数不一致")

    if custom_dict_path:
        try:
            import jieba
            jieba.load_userdict(custom_dict_path)
            logger.info(f"已加载中文自定义词典：{custom_dict_path}")
        except Exception as exc:
            logger.warning(f"加载中文自定义词典失败：{exc}")

    tokens_list: List[List[str]] = []
    empty_count = 0
    language_stats = {"zh": {"documents": 0, "tokens": 0}, "en": {"documents": 0, "tokens": 0}}
    for index, (text, language) in enumerate(zip(texts, languages)):
        language_stats[language]["documents"] += 1
        cleaned = clean_text(text, opts, language)
        if not cleaned or len(cleaned) < opts.min_text_length:
            tokens_list.append([])
            empty_count += 1
            continue
        if language == "zh":
            words = _tokenize_chinese(cleaned, opts.zh_min_token_length)
        elif language == "en":
            words = _tokenize_english(cleaned, opts.en_min_token_length)
        else:
            raise ValueError(f"不支持的文献语言：{language}")
        stopwords = stopwords_by_language.get(language, set())
        words = [word for word in words if word and word not in stopwords and not word.isspace()]
        tokens_list.append(words)
        language_stats[language]["tokens"] += len(words)
        if (index + 1) % 100 == 0:
            logger.info(f"已分词 {index + 1}/{len(texts)} 篇")

    all_tokens = [word for document in tokens_list for word in document]
    return tokens_list, {
        "total_docs": len(texts),
        "non_empty_docs": len(texts) - empty_count,
        "total_tokens": len(all_tokens),
        "unique_words": len(set(all_tokens)),
        "languages": language_stats,
    }


def tokenize_texts(
    texts: List[str], opts: CleanOptions, stopwords: Set[str], custom_dict_path: Optional[str] = None,
) -> Tuple[List[List[str]], dict]:
    """v1 PySide6 兼容包装：把未声明语言的旧调用视为中文。"""
    return tokenize_documents(texts, ["zh"] * len(texts), opts, {"zh": stopwords}, custom_dict_path)


def load_stopwords(path: str) -> Set[str]:
    stopwords = set()
    try:
        with open(path, "r", encoding="utf-8") as file:
            stopwords = {line.strip() for line in file if line.strip()}
        logger.info(f"加载停用词 {len(stopwords)} 个")
    except Exception as exc:
        logger.error(f"加载停用词文件失败：{exc}")
    return stopwords


def get_default_stopwords(language: str = "zh") -> Set[str]:
    if language == "en":
        return {
            "a", "an", "and", "are", "as", "at", "be", "been", "being", "but", "by",
            "can", "could", "did", "do", "does", "for", "from", "had", "has", "have", "he",
            "her", "hers", "him", "his", "i", "if", "in", "into", "is", "it", "its", "may",
            "might", "more", "most", "no", "not", "of", "on", "or", "our", "ours", "she",
            "should", "so", "some", "such", "than", "that", "the", "their", "theirs", "them",
            "then", "there", "these", "they", "this", "those", "to", "was", "we", "were", "what",
            "when", "where", "which", "who", "will", "with", "would", "you", "your", "yours",
        }
    return {
        "的", "了", "在", "是", "我", "有", "和", "就", "不", "人", "都", "一", "一个", "上",
        "也", "很", "到", "说", "要", "去", "你", "会", "着", "没有", "看", "好", "自己", "这",
        "那", "它", "他", "她", "这个", "那个", "这些", "那些", "什么", "怎么", "为什么", "因为",
        "所以", "但是", "而且", "可以", "这样", "如此", "等", "等等", "该", "其", "已", "将", "与",
        "及", "或", "以", "之", "于", "而", "且", "则", "乃", "若", "如", "虽", "然", "即", "年",
        "月", "日", "时", "分", "秒", "号", "期", "本", "各", "此", "某", "任", "每", "中", "内",
        "外", "下", "左", "右", "前", "后", "可", "能", "应", "当", "须", "必", "欲", "愿", "为",
        "因", "由", "从", "向", "对", "记者", "报道", "本报", "本刊", "编者", "读者",
    }
