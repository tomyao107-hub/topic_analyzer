# Task 2 Tauri 前端与 Python 计算层本地集成边界

## 目标

为后续 Tauri GUI 实现建立稳定、最小可落地的本地调用契约。前端负责交互、状态呈现和结果浏览；Python 计算层继续复用现有 `services/*.py`、`models/app_state.py` 和必要的页面内业务逻辑下沉结果，不改变现有输入格式、建模算法和导出语义。

## 边界原则

- Tauri 前端只传递用户输入、文件路径、参数、分页查询条件和导出选项。
- Python 层持有 `AppState`、pandas DataFrame、gensim 模型、rpy2 对象和文件写入逻辑。
- 前端不直接接收 DataFrame、模型对象或 R 对象，只接收 JSON 可序列化的摘要、分页表格、图表数据、文件路径和错误对象。
- 清洗、LDA、STM、批量导出等耗时操作统一走任务模型，前端通过任务状态轮询或事件流刷新忙碌、完成和失败反馈。
- 对比聚合和批量导出中仍在 PySide6 页面内的 pandas/file 写入逻辑，应迁入 Python 集成层或独立 service，避免 Tauri 前端重新实现业务语义。
- 迁移期保留现有 PySide6 入口，新集成层只新增适配代码，不破坏旧 GUI 对 service 和 `AppState` 的使用方式。

## 最小本地调用方式

第一阶段采用 Tauri sidecar 启动 Python 常驻进程，Rust 命令通过 stdin/stdout JSON Lines 与 Python 集成入口通信。

- 启动方式：Tauri 启动时拉起 `python -m backend.bridge` 或打包后的 Python sidecar。
- 通信协议：每行一个 JSON 请求或响应，使用 `id` 关联请求，避免引入 HTTP 服务、端口占用和 CORS 配置。
- 任务执行：Python 进程内使用线程或进程池执行耗时任务，任务结果写回 `AppState`，stdout 返回任务事件和状态快照。
- 调试方式：开发期可直接在终端运行 Python bridge，手动输入 JSON Lines 复现单个命令。
- 后续演进：如需要多窗口、多客户端或外部自动化，再升级为本机 HTTP/WebSocket；当前规格优先保证本地桌面、开发调试简单和 Python 逻辑复用。

## 请求与响应信封

### 请求

```json
{
  "id": "req_001",
  "command": "import.load_table",
  "payload": {
    "role": "metadata",
    "path": "E:/data/meta.csv"
  }
}
```

### 成功响应

```json
{
  "id": "req_001",
  "ok": true,
  "data": {
    "summary": {}
  },
  "state": {}
}
```

### 失败响应

```json
{
  "id": "req_001",
  "ok": false,
  "error": {
    "code": "UNSUPPORTED_FILE_TYPE",
    "message": "不支持的文件格式：.txt，请使用 .csv 或 .xlsx",
    "detail": "原始异常或可展开诊断文本",
    "recoverable": true,
    "suggestion": "请选择 CSV、XLSX 或 XLS 文件"
  },
  "state": {}
}
```

## 全局状态快照

所有会改变工作流的命令返回 `state`，用于前端同步导航、页面可用性和摘要卡片。

```json
{
  "workflow": {
    "imported": true,
    "merged": true,
    "cleaned": false,
    "ldaDone": false,
    "stmDone": false
  },
  "session": {
    "projectName": "未命名项目",
    "outputDir": ""
  },
  "data": {
    "metadataRows": 1200,
    "textRows": 1198,
    "mergedRows": 1180,
    "unmatchedMetaRows": 20,
    "unmatchedTextRows": 18
  },
  "clean": {
    "documents": 1180,
    "nonEmptyDocuments": 0,
    "totalTokens": 0,
    "uniqueWords": 0
  },
  "models": {
    "lda": {
      "available": false,
      "topicCount": 0,
      "coherence": null
    },
    "stm": {
      "available": false,
      "topicCount": 0,
      "rAvailable": null
    }
  }
}
```

## 任务状态结构

清洗、LDA、STM、批量导出、pyLDAvis 生成等耗时动作统一返回 `taskId`。前端通过 `task.get` 查询，或订阅 bridge 输出的 `task.event` 行。

```json
{
  "taskId": "task_lda_001",
  "type": "lda.train",
  "status": "running",
  "phase": "training",
  "message": "正在训练 LDA 模型",
  "progress": {
    "current": null,
    "total": null,
    "percent": null
  },
  "startedAt": "2026-07-03T10:00:00+08:00",
  "finishedAt": null,
  "result": null,
  "error": null
}
```

`status` 取值为 `queued`、`running`、`succeeded`、`failed`、`cancelled`。现有 service 大多无法提供精确百分比时，`progress.percent` 可为 `null`，前端展示阶段文案和不确定进度。

## 命令契约

### 会话

| Command | Payload | Data |
| --- | --- | --- |
| `session.get_state` | `{}` | 全局状态快照 |
| `session.reset` | `{}` | 重置后的全局状态快照 |
| `session.update_config` | `{ "projectName": string, "outputDir": string }` | 会话配置摘要 |
| `system.check_dependencies` | `{ "targets": ["jieba", "gensim", "pyldavis", "r"] }` | 依赖可用性和安装提示 |

### 导入与合并

| Command | Payload | Data |
| --- | --- | --- |
| `import.load_table` | `{ "role": "metadata" | "text", "path": string }` | 文件摘要、字段识别结果、预览行 |
| `import.detect_columns` | `{ "role": "metadata" | "text" }` | 字段映射、缺失必填字段、未识别字段 |
| `import.merge` | `{}` | 合并行数、未匹配统计、预览行 |
| `table.preview` | `{ "table": "metadata" | "text" | "merged" | "cleaned" | "ldaDocTopics" | "stmDocTopics", "page": number, "pageSize": number }` | 分页表格、列名、总行数 |

`import.load_table` 对应 `services.data_service.load_file`、`detect_meta_columns`、`detect_text_columns`。`import.merge` 对应 `merge_tables`，并写入 `AppState` 的导入与合并字段。

### 清洗与分词

| Command | Payload | Data |
| --- | --- | --- |
| `clean.load_stopwords` | `{ "path": string }` | 停用词数量、路径、警告 |
| `clean.set_custom_dict` | `{ "path": string | null }` | 当前自定义词典路径 |
| `clean.preview` | `{ "options": CleanOptionsPayload, "rowIndex": number }` | 原文、清洗后文本、分词样例 |
| `clean.run` | `{ "options": CleanOptionsPayload, "stopwords": string[], "customDictPath": string | null }` | `taskId` |

`CleanOptionsPayload` 映射到 `services.clean_service.CleanOptions`，字段包括 `removeEmpty`、`removeDuplicates`、`ocrClean`、`removePunct`、`removeNumbers`、`traditionalToSimplified`、`minTextLength`、`minTokenFreq`、`minDocFreq`、`maxDocFreqRatio`。

### LDA

| Command | Payload | Data |
| --- | --- | --- |
| `lda.train` | `{ "numTopics": number, "passes": number, "iterations": number, "randomState": number, "minFreq": number, "minDocFreq": number, "maxDocFreqRatio": number, "genreFilter": string | null }` | `taskId` |
| `lda.get_result` | `{}` | 主题关键词、coherence、文档主题摘要 |
| `lda.open_pyldavis` | `{ "outputDir": string }` | `taskId` |
| `lda.export` | `{ "outputDir": string }` | 导出文件列表 |

`lda.train` 复用 `build_corpus`、`train_lda`、`get_topics`、`get_doc_topics`、`compute_coherence`，并在 Python 进程内保留 `lda_model`、`lda_dictionary` 和 `lda_corpus`。

### STM

| Command | Payload | Data |
| --- | --- | --- |
| `stm.check_r` | `{}` | R/rpy2/stm 可用性、版本或安装指引 |
| `stm.analyze_covariates` | `{}` | 可用于 prevalence/content 的字段、不可用原因 |
| `stm.train` | `{ "numTopics": number, "maxEmIts": number, "seed": number, "genreFilter": string | null, "prevalenceFormula": string, "contentCovariate": string | null }` | `taskId` |
| `stm.get_result` | `{}` | 主题关键词、文档主题摘要、prevalence 摘要 |
| `stm.export` | `{ "outputDir": string }` | 导出文件列表 |

`stm.analyze_covariates` 应下沉当前 `gui/pages/stm_page.py` 的协变量可用性判断。`stm.train` 复用 `check_r_environment`、`train_stm` 和 `save_stm_results`。

### 对比分析

| Command | Payload | Data |
| --- | --- | --- |
| `compare.get_filters` | `{}` | 报刊、年份、文类、主题、可用模型 |
| `compare.build_summary` | `{ "model": "auto" | "lda" | "stm", "axisField": "newspaper" | "pub_year" | "time_index" | "genre" | "dominant_topic", "topic": string | null, "filters": CompareFilters }` | 图表序列、聚合表、代表文章 |
| `compare.export_chart_data` | `{ "path": string, "summary": object }` | 导出文件路径 |

`compare.build_summary` 应复用并下沉 `build_topic_summary` 的 pandas 聚合语义，返回前端图表库可直接消费的 `categories`、`series` 和代表文章列表。

### 导出与日志

| Command | Payload | Data |
| --- | --- | --- |
| `export.list_items` | `{}` | 当前可导出项目、是否可用、缺失原因 |
| `export.run` | `{ "outputDir": string, "projectName": string, "items": string[] }` | `taskId` |
| `logs.tail` | `{ "limit": number }` | 最近日志行 |
| `logs.clear` | `{}` | 清空结果 |

批量导出应把 `gui/pages/export_page.py` 中的写文件逻辑迁入 Python 集成层或 `services/export_service.py`，返回 `exported` 和 `errors`，允许部分成功。

## 结果摘要结构

### 表格预览

```json
{
  "columns": ["doc_id", "article_title", "newspaper", "pub_year"],
  "rows": [
    { "doc_id": "001", "article_title": "标题", "newspaper": "申报", "pub_year": 1932 }
  ],
  "page": 1,
  "pageSize": 50,
  "totalRows": 1180
}
```

### 主题结果

```json
{
  "topics": [
    {
      "topicId": 0,
      "label": "主题1: 教育 学校 学生",
      "words": [
        { "word": "教育", "weight": 0.034 }
      ]
    }
  ],
  "docTopicPreview": {},
  "metrics": {
    "coherence": 0.5123
  }
}
```

### 导出结果

```json
{
  "exported": [
    { "item": "merged_data", "path": "E:/out/merged_data.csv" }
  ],
  "errors": [
    { "item": "stm_prevalence", "message": "尚未完成 STM 训练" }
  ]
}
```

## 错误码约定

| Code | 场景 |
| --- | --- |
| `UNSUPPORTED_FILE_TYPE` | 文件扩展名不是 CSV/XLS/XLSX |
| `FILE_DECODE_FAILED` | CSV 多编码尝试失败 |
| `EXCEL_EMPTY` | Excel 无可读取工作表 |
| `REQUIRED_FIELD_MISSING` | 缺少 `doc_id`、`text` 等必填字段 |
| `PRECONDITION_FAILED` | 未合并、未清洗、未训练等前置步骤缺失 |
| `EMPTY_TRAINING_SET` | 筛选或清洗后无有效建模文档 |
| `DEPENDENCY_MISSING` | jieba、gensim、pyLDAvis、rpy2、R 或 R stm 缺失 |
| `TASK_FAILED` | 长任务内部异常 |
| `EXPORT_PARTIAL_FAILED` | 批量导出部分成功、部分失败 |
| `UNKNOWN_ERROR` | 未分类异常 |

## 前端状态使用约定

- 导航完成态只依赖 `state.workflow`，不从页面局部结果反推。
- 主按钮可用性由 `state.workflow` 和最近任务状态共同决定。
- 页面表格通过 `table.preview` 分页读取，避免一次性传输大数据集。
- 图表使用 `compare.build_summary`、`lda.get_result` 和 `stm.get_result` 的序列化结果，不在前端重复运行 pandas 聚合。
- 错误弹窗展示 `error.message`，详情展开展示 `error.detail` 和 `error.suggestion`。

## 后续实现落点

- 新增 Python 集成入口：`backend/bridge.py`，负责 JSON Lines 读写、命令分发、任务注册和状态序列化。
- 新增 Python 适配层：`backend/commands/*.py`，按导入、清洗、LDA、STM、对比、导出拆分命令处理。
- 可新增 `services/export_service.py` 和 `services/compare_service.py`，承接当前页面内导出和对比聚合逻辑。
- Tauri Rust 层只负责启动 sidecar、发送命令、转发事件和暴露 `invoke` 命令给前端。
- 前端状态管理以 `state.workflow`、任务列表和页面局部表单为核心，不保存大体积数据副本。
