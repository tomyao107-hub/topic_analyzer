# 历史文献主题分析工具 v2

面向数字人文与历史研究的中英文主题分析桌面工具。v2 使用一张文献表完成导入、清洗、LDA、STM、历史元数据对比和分语言导出。

## v2 核心变化

- 单表导入：不再接受“元数据表 + 文本表”双文件协议。
- 双语预处理：中文使用 jieba；英文进行 Unicode 规范化、小写化、跨行断词修复和拉丁词分词。
- 分语言建模：中文和英文拥有独立词表、LDA/STM 配置与结果。
- 广义历史元数据：支持报刊、书信、日记、档案等材料，并保留所有自定义字段。
- 可复现导出：`session_config.json` 使用 `schemaVersion: 2`，模型结果写入 `zh/`、`en/` 子目录。

## 输入格式

支持 CSV、XLSX、XLS；Excel 读取第一张工作表。一行必须对应一篇分析文献。

必填字段：

| 标准字段 | 含义 | 常见别名 |
|---|---|---|
| `doc_id` | 唯一文献编号 | 文献编号、文档编号、id |
| `text` | 正文 | 正文、正文文本、content |
| `language` | 语料语言 | 语言、语种、lang |

`language` 会规范化为 `zh` 或 `en`。支持中文、Chinese、zh-CN、英文、English、en-US、en-GB 等常见值；缺失或未知值会阻止导入，系统不会自动猜测。

推荐可选字段：

```text
title, creator, date, source_name, source_type, genre, place,
collection, repository, volume, issue, page, notes, year, month, time_index
```

旧字段名可以出现在新的单表中，例如 `article_title`、`author`、`newspaper`、`pub_date`，系统会映射到新的通用字段。其他列原样保留，可用于 STM 协变量和对比分析。

## 分析规则

- 原始 `text` 永不覆盖；清洗结果写入 `cleaned_text`。
- 中文最短 token 默认 1 个汉字，可使用停用词、自定义词典和繁简转换。
- 英文默认保留词形和历史拼写，不做 stemming 或 lemmatization。
- 词频和文档频率按语言分别计算。
- 混合语料项目训练模型时必须选择 `zh` 或 `en`，不允许跨语言比较主题编号。
- STM 默认 prevalence 公式为 `~ 1`。

## 启动

v2 默认界面为 React + Tauri：

```bat
run.bat
```

或手动启动：

```bash
cd desktop
npm install
npm run tauri dev
```

需要 Node.js、Rust、Python 3.11+；Python 依赖通过根目录 `requirements.txt` 安装。STM 另外需要 R、rpy2 和 R `stm` 包。

旧 PySide6 v1 仅作为回退参考，不提供单表或双语能力：

```bat
run-legacy.bat
```

## 导出结构

```text
documents.csv
cleaned_documents.csv
zh/
  tokens_corpus.txt
  lda_topic_word.csv
  lda_doc_topic.csv
  lda_coherence.json
  stm_topic_word.csv
  stm_doc_topic.csv
  stm_topic_prevalence.csv
en/
  ...同结构...
session_config.json
```

## 开发验证

```bat
.venv\Scripts\python.exe -m pytest -q
cd desktop
npm run build
cargo check --manifest-path src-tauri\Cargo.toml
```

本版不直接读取 PDF、Word 或扫描图像，不提供 OCR 识别、自动语言识别、翻译或跨语言主题对齐。
