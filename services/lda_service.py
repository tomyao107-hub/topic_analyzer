"""
LDA 建模服务
使用 gensim 进行 LDA 主题建模，支持 coherence 评估和 pyLDAvis 可视化
"""
import os
import json
from typing import List, Dict, Optional, Tuple, Any
import pandas as pd
import numpy as np

from utils.logger import get_logger

logger = get_logger()


def build_corpus(
    tokens_list: List[List[str]],
    min_freq: int = 2,
    min_doc_freq: int = 2,
    max_doc_freq_ratio: float = 0.95,
) -> Tuple[Any, Any, List[List[str]]]:
    """
    构建 gensim Dictionary 和 BoW 语料
    返回 (dictionary, corpus, filtered_tokens)
    """
    try:
        from gensim import corpora
    except ImportError:
        raise ImportError("gensim 未安装，请运行：pip install gensim")

    # 过滤空文档
    filtered = [t for t in tokens_list if len(t) >= 3]
    if not filtered:
        raise ValueError("有效文档数量为 0，请检查清洗与分词设置")

    dictionary = corpora.Dictionary(filtered)

    # 过滤低频词和高频词
    dictionary.filter_extremes(
        no_below=min_doc_freq,
        no_above=max_doc_freq_ratio,
    )

    corpus = [dictionary.doc2bow(doc) for doc in filtered]

    logger.info(
        f"语料构建完成：{len(corpus)} 个文档，"
        f"词典大小 {len(dictionary)} 词"
    )
    return dictionary, corpus, filtered


def train_lda(
    corpus: Any,
    dictionary: Any,
    num_topics: int = 10,
    passes: int = 20,
    iterations: int = 400,
    random_state: int = 42,
    alpha: str = "auto",
    eta: str = "auto",
) -> Any:
    """
    训练 LDA 模型
    """
    try:
        from gensim.models import LdaModel
    except ImportError:
        raise ImportError("gensim 未安装")

    logger.info(f"开始训练 LDA，主题数={num_topics}，passes={passes}...")
    model = LdaModel(
        corpus=corpus,
        id2word=dictionary,
        num_topics=num_topics,
        passes=passes,
        iterations=iterations,
        random_state=random_state,
        alpha=alpha,
        eta=eta,
        chunksize=2000,
        update_every=1,
    )
    logger.info("LDA 训练完成")
    return model


def get_topics(model: Any, n_words: int = 20) -> List[Dict]:
    """
    提取每个主题的关键词列表
    返回 [{"topic_id": int, "words": [(word, prob), ...], "label": str}, ...]
    """
    topics = []
    for tid in range(model.num_topics):
        word_probs = model.show_topic(tid, topn=n_words)
        words = [(w, float(p)) for w, p in word_probs]
        label = " ".join([w for w, _ in words[:5]])
        topics.append({
            "topic_id": tid,
            "words": words,
            "label": f"主题{tid+1}: {label}",
        })
    return topics


def get_doc_topics(
    model: Any,
    corpus: Any,
    merged_df: Optional[pd.DataFrame] = None,
    filtered_indices: Optional[List[int]] = None,
) -> pd.DataFrame:
    """
    计算每篇文档的主题分布
    返回 DataFrame，列为 [doc_id, topic_0, topic_1, ..., dominant_topic]
    """
    n_topics = model.num_topics
    rows = []

    for i, bow in enumerate(corpus):
        topic_dist = dict(model.get_document_topics(bow, minimum_probability=0.0))
        row = {f"topic_{t}": topic_dist.get(t, 0.0) for t in range(n_topics)}
        row["dominant_topic"] = max(row, key=row.get).replace("topic_", "主题")
        rows.append(row)

    df = pd.DataFrame(rows)

    # 合并文档元数据
    if merged_df is not None and filtered_indices is not None:
        meta_cols = [c for c in [
            "doc_id", "article_title", "newspaper", "pub_date",
            "pub_year", "pub_month", "time_index", "genre"
        ] if c in merged_df.columns]
        sub_meta = merged_df.iloc[filtered_indices][meta_cols].reset_index(drop=True)
        df = pd.concat([sub_meta, df], axis=1)

    return df


def compute_coherence(
    model: Any,
    corpus: Any,
    dictionary: Any,
    tokens_list: List[List[str]],
    coherence: str = "c_v",
) -> float:
    """
    计算主题一致性（coherence）
    """
    try:
        from gensim.models import CoherenceModel
    except ImportError:
        return float("nan")

    try:
        cm = CoherenceModel(
            model=model,
            texts=tokens_list,
            dictionary=dictionary,
            coherence=coherence,
        )
        score = cm.get_coherence()
        logger.info(f"Coherence ({coherence}) = {score:.4f}")
        return score
    except Exception as e:
        logger.warning(f"计算 coherence 失败：{e}")
        return float("nan")


def open_pyldavis(model: Any, corpus: Any, dictionary: Any, output_dir: str) -> str:
    """
    生成 pyLDAvis HTML 并返回路径（在浏览器中打开）
    """
    try:
        import pyLDAvis
        import pyLDAvis.gensim_models as gensimvis
    except ImportError:
        raise ImportError("pyLDAvis 未安装，请运行：pip install pyldavis")

    import webbrowser
    os.makedirs(output_dir, exist_ok=True)
    out_path = os.path.join(output_dir, "lda_vis.html")

    logger.info("生成 pyLDAvis 可视化...")
    # mmds avoids the complex eigenvalues that PCoA can produce on very small
    # or highly symmetric corpora, which otherwise cannot be serialized to JSON.
    vis = gensimvis.prepare(model, corpus, dictionary, sort_topics=False, mds="mmds")
    pyLDAvis.save_html(vis, out_path)
    logger.info(f"pyLDAvis 已保存至 {out_path}")
    webbrowser.open(f"file://{os.path.abspath(out_path)}")
    return out_path


def save_lda_results(
    topics: List[Dict],
    doc_topics_df: pd.DataFrame,
    coherence: float,
    output_dir: str,
):
    """导出 LDA 结果到 CSV/JSON"""
    os.makedirs(output_dir, exist_ok=True)

    # topic_word.csv
    rows = []
    for t in topics:
        for rank, (word, prob) in enumerate(t["words"]):
            rows.append({"topic_id": t["topic_id"], "rank": rank + 1,
                         "word": word, "probability": round(prob, 6)})
    pd.DataFrame(rows).to_csv(os.path.join(output_dir, "lda_topic_word.csv"),
                               index=False, encoding="utf-8-sig")

    # doc_topic.csv
    doc_topics_df.to_csv(os.path.join(output_dir, "lda_doc_topic.csv"),
                          index=False, encoding="utf-8-sig")

    # coherence.json
    with open(os.path.join(output_dir, "lda_coherence.json"), "w", encoding="utf-8") as f:
        json.dump({"coherence_c_v": coherence}, f, ensure_ascii=False, indent=2)

    logger.info(f"LDA 结果已导出至 {output_dir}")
