"""
文本清洗与分词服务
支持中文 OCR 文本清洗、jieba 分词、停用词处理
"""
import re
from typing import List, Optional, Set, Tuple
import pandas as pd

from utils.logger import get_logger

logger = get_logger()

# 默认 OCR 噪声正则模式
DEFAULT_OCR_PATTERNS = [
    r"[□■◆◇▲△○●◎]",          # 常见 OCR 噪声符号
    r"[①②③④⑤⑥⑦⑧⑨⑩]",        # 带圈数字
    r"\s{2,}",                  # 多余空白（替换为单空格）
    r"[^\u4e00-\u9fff\u3400-\u4dbf\uff00-\uffef\u2e80-\u2eff"
    r"\u31c0-\u31ef\u3200-\u32ff\u3300-\u33ff\uac00-\ud7af"
    r'''a-zA-Z0-9\s，。！？、；：""''（）《》【】—…·-]''',  # 非中英文符号
]

# 标点符号正则
PUNCT_PATTERN = re.compile(
    r'''[，。！？、；：""''（）《》【】—…·「」『』〔〕〖〗,\.!?;:"'()\[\]{}_@#$%^&*+=<>/\\|~`-]'''
)

# 数字正则
NUMBER_PATTERN = re.compile(r"\d+")


class CleanOptions:
    """清洗选项配置"""
    def __init__(self):
        self.remove_empty = True
        self.remove_duplicates = True
        self.ocr_clean = True
        self.ocr_patterns = DEFAULT_OCR_PATTERNS.copy()
        self.remove_punct = True
        self.remove_numbers = True
        self.traditional_to_simplified = False
        self.min_text_length = 10       # 最短文本长度
        self.min_token_freq = 2          # 最小词频（构建词典时用）
        self.min_doc_freq = 2            # 最小文档频率
        self.max_doc_freq_ratio = 0.95   # 最大文档频率比例


def clean_text(text: str, opts: CleanOptions) -> str:
    """
    对单篇文本执行清洗流程
    """
    if not isinstance(text, str):
        return ""

    result = text

    # OCR 噪声清洗
    if opts.ocr_clean:
        for pat in opts.ocr_patterns:
            try:
                result = re.sub(pat, " ", result)
            except re.error:
                pass

    # 繁简转换（需要 opencc-python-reimplemented）
    if opts.traditional_to_simplified:
        try:
            import opencc
            converter = opencc.OpenCC("t2s.json")
            result = converter.convert(result)
        except ImportError:
            logger.warning("opencc 未安装，跳过繁简转换。请安装：pip install opencc-python-reimplemented")

    # 去除标点
    if opts.remove_punct:
        result = PUNCT_PATTERN.sub(" ", result)

    # 去除数字
    if opts.remove_numbers:
        result = NUMBER_PATTERN.sub(" ", result)

    # 折叠多余空白
    result = re.sub(r"\s+", " ", result).strip()

    return result


def tokenize_texts(
    texts: List[str],
    opts: CleanOptions,
    stopwords: Set[str],
    custom_dict_path: Optional[str] = None,
) -> Tuple[List[List[str]], dict]:
    """
    对文本列表进行分词
    返回 (tokens_list, stats)
    """
    try:
        import jieba
    except ImportError:
        raise ImportError("jieba 未安装，请运行：pip install jieba")

    # 加载自定义词典
    if custom_dict_path:
        try:
            jieba.load_userdict(custom_dict_path)
            logger.info(f"已加载自定义词典：{custom_dict_path}")
        except Exception as e:
            logger.warning(f"加载自定义词典失败：{e}")

    tokens_list = []
    empty_count = 0

    for i, text in enumerate(texts):
        cleaned = clean_text(text, opts)
        if not cleaned or len(cleaned) < opts.min_text_length:
            tokens_list.append([])
            empty_count += 1
            continue

        # jieba 精确模式分词
        words = list(jieba.cut(cleaned, cut_all=False))

        # 过滤停用词和短词
        words = [
            w.strip() for w in words
            if w.strip()
            and len(w.strip()) >= 2
            and w.strip() not in stopwords
            and not w.strip().isspace()
        ]

        tokens_list.append(words)

        if (i + 1) % 100 == 0:
            logger.info(f"  已分词 {i+1}/{len(texts)} 篇...")

    # 统计
    all_tokens = [w for doc in tokens_list for w in doc]
    unique_words = set(all_tokens)
    stats = {
        "total_docs": len(texts),
        "non_empty_docs": len(texts) - empty_count,
        "total_tokens": len(all_tokens),
        "unique_words": len(unique_words),
    }
    logger.info(
        f"分词完成：{stats['non_empty_docs']} 篇有效，"
        f"共 {stats['total_tokens']} 个 token，"
        f"{stats['unique_words']} 个唯一词"
    )
    return tokens_list, stats


def load_stopwords(path: str) -> Set[str]:
    """从文件加载停用词，支持每行一词"""
    stopwords = set()
    try:
        with open(path, "r", encoding="utf-8") as f:
            for line in f:
                word = line.strip()
                if word:
                    stopwords.add(word)
        logger.info(f"加载停用词 {len(stopwords)} 个")
    except Exception as e:
        logger.error(f"加载停用词文件失败：{e}")
    return stopwords


def get_default_stopwords() -> Set[str]:
    """内置常用中文停用词"""
    words = [
        "的", "了", "在", "是", "我", "有", "和", "就", "不", "人", "都",
        "一", "一个", "上", "也", "很", "到", "说", "要", "去", "你", "会",
        "着", "没有", "看", "好", "自己", "这", "那", "它", "他", "她",
        "这个", "那个", "这些", "那些", "什么", "怎么", "为什么", "因为",
        "所以", "但是", "而且", "可以", "这样", "如此", "等", "等等",
        "该", "其", "已", "将", "与", "及", "或", "以", "之", "于",
        "而", "且", "则", "乃", "若", "如", "虽", "然", "则", "即",
        "年", "月", "日", "时", "分", "秒", "号", "期",
        "本", "其", "各", "此", "该", "某", "任", "每",
        "中", "内", "外", "上", "下", "左", "右", "前", "后",
        "可", "能", "应", "当", "须", "必", "欲", "愿",
        "为", "因", "以", "由", "从", "向", "对",
        "记者", "报道", "本报", "本刊", "编者", "读者",
    ]
    return set(words)
