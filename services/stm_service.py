"""
STM（Structural Topic Model）建模服务
通过 rpy2 调用 R 的 stm 包实现真正的结构主题模型

rpy2 兼容说明：
- rpy2 >= 3.5 废弃了 pandas2ri.activate() / numpy2ri.activate()
- localconverter 基于 ContextVar，在 QThread 中上下文不会传播，
  因此本模块采用手动逐列转换（_df_to_r_manual），完全避开 ContextVar。
"""
import os
import re
import locale
from typing import List, Dict, Optional, Tuple, Any
import pandas as pd
import numpy as np
from utils.logger import get_logger

logger = get_logger()

_RPY2_READY = False
_R_STM_READY = False

R_INSTALL_GUIDE = """
══════════════════════════════════════════════════════
  STM 需要 R + stm 包 + rpy2，请按以下步骤安装：

  1. 安装 R（>= 4.0）：  https://cran.r-project.org/
  2. 在 R 控制台安装 stm 包：
       install.packages("stm")
  3. 安装 rpy2（Python 端）：  pip install rpy2
  4. Windows 用户设置 R_HOME 环境变量：
       R_HOME=C:\\Program Files\\R\\R-4.x.x
       并将 R\\bin\\x64 加入 PATH
  5. 重新启动本应用。
══════════════════════════════════════════════════════
"""


def _build_rpy2_init_error(exc: Exception) -> RuntimeError:
    """将常见编码错误补充为更可理解的初始化失败提示。"""
    msg = str(exc)
    hints = []

    lowered = msg.lower()
    if "codec can't decode" in lowered or "unicode" in lowered or "gbk" in lowered:
        pref = locale.getpreferredencoding(False)
        hints.append(
            "检测到编码解码失败，这通常是 Windows 下 R / rpy2 / 环境变量输出使用了非 UTF-8 编码导致。"
        )
        hints.append(f"当前系统首选编码：{pref}")
        hints.append("建议尝试：将系统区域设置改为 UTF-8，或在启动前设置 PYTHONUTF8=1。")
        hints.append("如果已配置 R_HOME / PATH，请避免路径或用户目录中出现异常编码字符。")

    detail = f"rpy2 初始化失败：{msg}"
    if hints:
        detail += "\n" + "\n".join(hints)
    return RuntimeError(detail + "\n" + R_INSTALL_GUIDE)


def _import_rpy2():
    """集中导入 rpy2，避免在各函数中分散初始化。"""
    global _RPY2_READY
    try:
        import rpy2.robjects as ro
        from rpy2.robjects.packages import importr
        _ = ro.default_converter
        _RPY2_READY = True
        return ro, importr
    except ImportError:
        raise ImportError("rpy2 未安装。" + R_INSTALL_GUIDE)
    except Exception as e:
        raise _build_rpy2_init_error(e)


def _ensure_stm_package():
    """集中初始化 R 侧 stm 包，减少线程环境下的重复初始化风险。"""
    global _R_STM_READY
    ro, importr = _import_rpy2()
    if not _R_STM_READY:
        try:
            importr("stm")
            _R_STM_READY = True
        except Exception as e:
            raise RuntimeError(
                "R stm 包未安装。\n"
                "请在 R 控制台运行：install.packages('stm')\n"
                f"错误：{e}"
            )
    return ro



# ─────────────────────────────────────────────────────────────
# 内部辅助：将 pandas DataFrame 转为 R data.frame
# ─────────────────────────────────────────────────────────────

def _df_to_r_manual(df: pd.DataFrame):
    """最终降级方案：手动逐列转换，不依赖 pandas2ri"""
    ro = _ensure_stm_package()
    r_cols = {}
    for col in df.columns:
        s = df[col]
        try:
            if pd.api.types.is_integer_dtype(s):
                r_cols[str(col)] = ro.IntVector(s.fillna(0).astype(int).tolist())
            elif pd.api.types.is_float_dtype(s):
                vals = [float('nan') if pd.isna(v) else float(v) for v in s.tolist()]
                r_cols[str(col)] = ro.FloatVector(vals)
            else:
                r_cols[str(col)] = ro.StrVector(s.fillna("").astype(str).tolist())
        except Exception:
            r_cols[str(col)] = ro.StrVector(s.fillna("").astype(str).tolist())
    return ro.DataFrame(r_cols)


def _py2r_df(df: pd.DataFrame):
    """
    将 pandas DataFrame 转为 R data.frame。

    注意：此函数可能在 QThread 中调用。rpy2 的 localconverter 基于
    ContextVar，在 Qt 子线程中上下文不会自动传播，导致
    "Conversion rules for 'rpy2.robjects' appear to be missing" 错误。
    因此这里直接使用手动逐列转换，完全避开 localconverter / ContextVar。
    """
    return _df_to_r_manual(df)


# ─────────────────────────────────────────────────────────────
# 环境检测
# ─────────────────────────────────────────────────────────────

def check_r_environment() -> Tuple[bool, str]:
    try:
        ro = _ensure_stm_package()
    except Exception as e:
        return False, str(e)

    try:
        r_version = ro.r('R.Version()$version.string')[0]
        logger.info(f"R 版本：{r_version}")
    except Exception as e:
        return False, f"无法调用 R：{e}\n" + R_INSTALL_GUIDE

    return True, f"R 环境正常，{r_version}"


# ─────────────────────────────────────────────────────────────
# STM 训练主函数
# ─────────────────────────────────────────────────────────────

def train_stm(
    merged_df: pd.DataFrame,
    tokens_list: List[List[str]],
    num_topics: int = 10,
    prevalence_formula: str = "~ 1",
    content_covariate: Optional[str] = None,
    seed: int = 42,
    max_em_its: int = 75,
) -> Tuple[Any, List[Dict], pd.DataFrame, pd.DataFrame]:
    """训练 STM 模型，返回 (r_model, topics, doc_topics_df, prevalence_df)"""
    from collections import Counter

    ro = _ensure_stm_package()

    logger.info("准备 STM 输入数据...")

    # 构建词汇表（doc freq >= 2）
    word_freq: Counter = Counter()
    for tokens in tokens_list:
        word_freq.update(set(tokens))

    vocab_list = sorted([w for w, f in word_freq.items() if f >= 2])
    vocab_set  = set(vocab_list)
    word2id    = {w: i for i, w in enumerate(vocab_list)}
    # Windows/R 的系统区域设置可能把中文词表全部转成 "??"。R 侧只需要
    # 唯一标签来维持词元索引，因此使用 ASCII 安全标签训练，提取结果后再映射回原词。
    r_vocab_list = [f"term_{index:06d}" for index in range(len(vocab_list))]
    r_to_original = dict(zip(r_vocab_list, vocab_list))

    if not vocab_list:
        raise ValueError("词汇表为空，请检查分词和词频过滤设置")

    # 构建 stm 要求的稀疏文档格式（2×N 整数矩阵：行1=词ID, 行2=词频）
    doc_list_r   = []
    valid_indices = []
    for idx, tokens in enumerate(tokens_list):
        filtered = [w for w in tokens if w in vocab_set]
        if len(filtered) < 2:
            continue
        cnt = Counter(filtered)
        # 按列展开：[id1, cnt1, id2, cnt2, ...]
        flat = []
        for w, c in cnt.items():
            flat.append(word2id[w] + 1)   # R 1-indexed
            flat.append(c)
        mat = ro.r.matrix(ro.IntVector(flat), nrow=2, byrow=False)
        doc_list_r.append(mat)
        valid_indices.append(idx)

    if not doc_list_r:
        raise ValueError("有效文档数为 0，请降低过滤阈值或检查分词结果")

    logger.info(f"有效文档：{len(doc_list_r)}，词汇量：{len(vocab_list)}")

    r_docs  = ro.ListVector({str(i + 1): d for i, d in enumerate(doc_list_r)})
    r_vocab = ro.StrVector(r_vocab_list)

    sub_df = merged_df.iloc[valid_indices].reset_index(drop=True)
    formula_str = _validate_stm_formula_metadata(sub_df, prevalence_formula, role="prevalence")

    content_line = ""
    if content_covariate and content_covariate.strip():
        content_name = content_covariate.strip().replace("`", "")
        content_formula = _validate_stm_formula_metadata(
            sub_df, f"~ `{content_name}`", role="content"
        )
        content_line = f"content = {content_formula},"

    r_meta = _py2r_df(sub_df)

    ro.globalenv["stm_docs"]  = r_docs
    ro.globalenv["stm_vocab"] = r_vocab
    ro.globalenv["stm_meta"]  = r_meta

    r_code = f"""
    set.seed({seed})
    stm_model <- stm(
      documents  = stm_docs,
      vocab      = stm_vocab,
      K          = {num_topics},
      prevalence = {formula_str},
      {content_line}
      data       = stm_meta,
      max.em.its = {max_em_its},
      init.type  = "Spectral",
      verbose    = FALSE
    )
    """

    logger.info(f"调用 R stm，K={num_topics}，公式={formula_str}...")
    ro.r(r_code)
    r_model = ro.globalenv["stm_model"]

    # 主题关键词
    logger.info("提取 STM 主题关键词...")
    label_word_count = min(20, len(vocab_list))
    ro.r(f"stm_labels <- labelTopics(stm_model, n={label_word_count})")
    topics = _extract_stm_topics(ro.globalenv["stm_labels"], num_topics)
    for topic in topics:
        topic["words"] = [
            (r_to_original.get(word, word), weight)
            for word, weight in topic.get("words", [])
        ]
        visible_words = [word for word, _ in topic["words"][:5]]
        topic["label"] = f"主题{topic['topic_id'] + 1}: " + (" ".join(visible_words) if visible_words else "（无主题词）")

    # 文档主题分布
    logger.info("提取文档主题分布...")
    theta = np.array(ro.r("stm_model$theta"))
    doc_topics_df = _make_doc_topics_df(theta, sub_df, num_topics)

    # 协变量效应
    logger.info("估算协变量效应...")
    prevalence_df = _estimate_prevalence(sub_df, prevalence_formula, num_topics)

    logger.info("STM 训练完成")
    return r_model, topics, doc_topics_df, prevalence_df


# ─────────────────────────────────────────────────────────────
# 内部工具函数
# ─────────────────────────────────────────────────────────────

def _extract_stm_topics(labels_r: Any, num_topics: int) -> List[Dict]:
    topics = []
    try:
        if labels_r is None:
            raise ValueError("labelTopics 返回空对象")

        try:
            prob_words = labels_r.rx2("prob")
        except Exception as e:
            raise ValueError(f"无法读取 labelTopics$prob：{e}")

        if prob_words is None or type(prob_words).__name__ == "NULLType":
            raise ValueError("labelTopics$prob 为空")

        for tid in range(num_topics):
            try:
                words_r = prob_words.rx(tid + 1, True)
                if words_r is None or type(words_r).__name__ == "NULLType":
                    words = []
                else:
                    words = [str(w) for w in words_r if str(w).strip()]
            except Exception:
                words = []

            topics.append({
                "topic_id": tid,
                "words": [(w, 0.0) for w in words],
                "label": f"主题{tid+1}: " + (" ".join(words[:5]) if words else "（未成功提取主题词）"),
            })
    except Exception as e:
        logger.warning(f"提取 STM 主题词出错：{e}")
        topics = [{"topic_id": i, "words": [], "label": f"主题{i+1}"}
                  for i in range(num_topics)]
    return topics


def _make_doc_topics_df(theta: np.ndarray, sub_df: pd.DataFrame,
                        num_topics: int) -> pd.DataFrame:
    rows = []
    for row in theta:
        d = {f"topic_{t}": float(row[t]) for t in range(num_topics)}
        d["dominant_topic"] = f"主题{int(np.argmax(row)) + 1}"
        rows.append(d)
    df = pd.DataFrame(rows)
    excluded = {"text", "cleaned_text", "tokens", "token_count"}
    meta_cols = [c for c in sub_df.columns if c not in excluded]
    return pd.concat([sub_df[meta_cols].reset_index(drop=True), df], axis=1)


def _estimate_prevalence(sub_df: pd.DataFrame, prevalence_formula: str,
                         num_topics: int) -> pd.DataFrame:
    ro = _ensure_stm_package()
    try:
        r_meta_eff = _py2r_df(sub_df)
        ro.globalenv["stm_meta"] = r_meta_eff
        formula_str = prevalence_formula.strip()
        if not formula_str.startswith("~"):
            formula_str = "~ " + formula_str

        ro.r(f"""
        stm_effect <- estimateEffect(
          1:{num_topics} {formula_str},
          stmobj = stm_model, metadata = stm_meta, uncertainty = "Global"
        )
        """)

        covar = _extract_first_covariate(prevalence_formula)
        if covar and covar in sub_df.columns:
            rows = []
            for level in sub_df[covar].dropna().unique().tolist()[:20]:
                for tid in range(1, num_topics + 1):
                    try:
                        val = ro.r(f'mean(stm_effect$parameters[[{tid}]][[1]]$est)')[0]
                        rows.append({covar: str(level), "topic_id": tid - 1,
                                     "topic_label": f"主题{tid}",
                                     "prevalence_estimate": float(val)})
                    except Exception:
                        pass
            if rows:
                return pd.DataFrame(rows)
    except Exception as e:
        logger.warning(f"估算协变量效应失败（非致命）：{e}")
    return pd.DataFrame()


def _analyze_stm_column(df: pd.DataFrame, col: str) -> Tuple[bool, Optional[str]]:
    """分析单个字段是否适合作为 STM 协变量。"""
    if col not in df.columns:
        return False, "字段不存在"

    s = df[col]
    non_null = s.dropna()
    if non_null.empty:
        return False, "全为空"

    nunique = non_null.astype(str).nunique()
    if nunique <= 1:
        return False, "只有一个有效取值"

    if pd.api.types.is_numeric_dtype(s):
        finite = pd.to_numeric(s, errors="coerce").dropna()
        if finite.empty:
            return False, "无法转换为数值"
    else:
        as_text = non_null.astype(str).str.strip()
        if (as_text == "").all():
            return False, "全为空字符串"

    return True, None


def _extract_formula_variables(formula: str) -> List[str]:
    """从 STM 公式中提取可能的变量名，忽略函数名与数字常量。"""
    formula = (formula or "~ 1").strip()
    if not formula.startswith("~"):
        formula = "~ " + formula

    backticked = re.findall(r"`([^`]+)`", formula)
    remainder = re.sub(r"`[^`]+`", " ", formula)
    tokens = backticked + re.findall(r"[^\W\d]\w*", remainder, flags=re.UNICODE)
    ignored = {"s", "c", "I", "log", "factor", "as", "ns", "bs"}
    vars_found = []
    for token in tokens:
        if token in ignored:
            continue
        if token not in vars_found:
            vars_found.append(token)
    return vars_found


def _validate_stm_formula_metadata(df: pd.DataFrame, formula: str, role: str = "prevalence"):
    """
    检查 STM 公式涉及的元数据列是否可用于 R model.matrix。
    若存在问题，提前给出清晰错误，避免 R 侧报模糊错误。
    """
    formula = (formula or "~ 1").strip()
    if not formula.startswith("~"):
        formula = "~ " + formula

    if "::" in formula:
        raise ValueError(
            f"{role} 公式不支持 package::name 这类命名空间写法：{formula}"
        )

    variables = _extract_formula_variables(formula)
    if not variables:
        return formula

    missing = [col for col in variables if col not in df.columns]
    if missing:
        raise ValueError(
            f"{role} 公式引用了不存在的字段：{', '.join(missing)}。"
            f"可用字段为：{', '.join(map(str, df.columns))}"
        )

    issues = []
    for col in variables:
        ok, reason = _analyze_stm_column(df, col)
        if not ok:
            issues.append(f"{col}={reason}")

    if issues:
        raise ValueError(
            f"{role} 公式中的字段不适合建模：{'；'.join(issues)}。"
            f"建议先尝试 `~ 1`，或改用取值稳定且非空的字段。"
        )

    return formula


def _extract_first_covariate(formula: str) -> Optional[str]:
    variables = _extract_formula_variables(formula)
    return variables[0] if variables else None


def save_stm_results(topics, doc_topics_df, prevalence_df, output_dir):
    os.makedirs(output_dir, exist_ok=True)
    rows = []
    for t in topics:
        for rank, (word, _) in enumerate(t["words"]):
            rows.append({"topic_id": t["topic_id"], "rank": rank + 1, "word": word})
    pd.DataFrame(rows).to_csv(os.path.join(output_dir, "stm_topic_word.csv"),
                               index=False, encoding="utf-8-sig")
    doc_topics_df.to_csv(os.path.join(output_dir, "stm_doc_topic.csv"),
                          index=False, encoding="utf-8-sig")
    if prevalence_df is not None and not prevalence_df.empty:
        prevalence_df.to_csv(os.path.join(output_dir, "stm_topic_prevalence.csv"),
                              index=False, encoding="utf-8-sig")
    logger.info(f"STM 结果已导出至 {output_dir}")
