# Task 1 GUI 流程与复用边界梳理

## 目标

为 Tauri GUI 迁移建立现有 PySide6 工作流基线，明确前端必须覆盖的页面能力、共享状态字段、错误反馈，以及应继续复用的 Python 计算层能力。

## 现有 PySide6 用户流程

### 1. 导入与合并

- 页面：`gui/pages/import_page.py`
- 用户动作：分别拖拽或选择元数据表、文本表，支持 `.csv`、`.xlsx`、`.xls`。
- 后端能力：`services.data_service.load_file` 读取文件，`detect_meta_columns` 和 `detect_text_columns` 自动识别字段，`merge_tables` 按 `doc_id` 合并。
- 页面反馈：上传区展示文件名、行列数和首尾样本；字段识别区展示标准字段映射和缺失字段；合并后展示匹配文章数、未匹配元数据数和未匹配文本数。
- 状态写入：`metadata_df`、`text_df`、`meta_col_map`、`text_col_map`、`merged_df`、`unmatched_meta`、`unmatched_text`、`step_imported`、`step_merged`。
- 错误反馈：文件读取异常弹出“导入失败”；缺少 `doc_id` 时阻止合并并弹出错误；合并异常弹出“合并失败”。

### 2. 数据清洗与分词

- 页面：`gui/pages/clean_page.py`
- 用户动作：配置基础清洗、文本长度、文档频率、停用词、自定义词典，选择文章预览原文、清洗文本和分词结果。
- 后端能力：`services.clean_service.CleanOptions`、`clean_text`、`tokenize_texts`、`load_stopwords`、`get_default_stopwords`。
- 页面反馈：清洗任务在 `QThread` 中运行；显示忙碌状态、无限进度条、完成统计和错误弹窗。
- 状态写入：`tokens_list`、`cleaned_df`、`stopwords`、`stopwords_path`、`custom_dict_path`、`step_cleaned`。
- 错误反馈：未合并数据时提示先导入合并；分词异常弹出“清洗失败”；外部停用词和词典加载结果显示在页面标签中。

### 3. LDA 主题建模

- 页面：`gui/pages/lda_page.py`
- 用户动作：设置主题数、训练轮数、迭代次数、随机种子、词频过滤参数，可按文类筛选训练数据。
- 后端能力：`services.lda_service.build_corpus`、`train_lda`、`get_topics`、`get_doc_topics`、`compute_coherence`、`open_pyldavis`、`save_lda_results`。
- 页面反馈：训练在 `QThread` 中运行；显示阶段文案、无限进度条、Coherence、主题关键词、文档主题表、matplotlib 图表和 pyLDAvis 入口。
- 状态写入：`lda_model`、`lda_dictionary`、`lda_corpus`、`lda_topics`、`lda_doc_topics`、`lda_coherence`、`output_dir`、`step_lda_done`。
- 错误反馈：未分词时提示先清洗；筛选后无有效文档时提示调整文类或清洗参数；训练异常弹出“训练失败”。

### 4. STM 结构主题建模

- 页面：`gui/pages/stm_page.py`
- 用户动作：检查 R 环境，设置主题数、最大 EM 迭代、随机种子、文类筛选、prevalence 公式和 content 协变量。
- 后端能力：`services.stm_service.check_r_environment`、`train_stm`、`save_stm_results`，以及 `_analyze_stm_column` 用于协变量可用性判断。
- 页面反馈：R 环境横幅展示就绪或失败；协变量列表标记不可用字段及原因；训练在 `QThread` 中运行；结果包含主题关键词、文档主题表和协变量效应图。
- 状态写入：`r_available`、`stm_result`、`stm_topics`、`stm_doc_topics`、`stm_prevalence`、`output_dir`、`step_stm_done`。
- 错误反馈：未分词时提示先清洗；R 环境缺失时展示安装指引；公式字段不可用或训练失败时弹出“STM 训练失败”。

### 5. 对比分析

- 页面：`gui/pages/compare_page.py`
- 用户动作：选择报刊、年份、文类、主题、模型、横轴、纵轴和图表类型，刷新图表，导出当前图表，点击代表文章查看原文。
- 后端能力：页面内 `build_topic_summary` 聚合主题分布；依赖 `lda_doc_topics` 或 `stm_doc_topics` 作为结果输入。
- 页面反馈：缺少建模结果时显示空状态；图表生成失败时显示错误文案；代表文章表展示各主题 top 文档和原文。
- 状态读取：`merged_df`、`lda_topics`、`stm_topics`、`lda_doc_topics`、`stm_doc_topics`。
- 错误反馈：未生成图表时禁止导出并提示；图表保存失败弹出“导出失败”。

### 6. 批量导出与日志

- 页面：`gui/pages/export_page.py`
- 用户动作：选择导出目录、勾选导出项目、设置项目名称、导出结果，查看和清空处理日志。
- 后端能力：目前页面直接使用 pandas、json 和文件写入导出；LDA/STM 页面也可调用对应 service 的保存函数导出单模型结果。
- 页面反馈：导出完成弹窗列出成功文件和失败项目；日志面板订阅 `log_signals.message`。
- 状态读取/写入：读取 `merged_df`、`cleaned_df`、`tokens_list`、`lda_topics`、`lda_doc_topics`、`lda_coherence`、`stm_topics`、`stm_doc_topics`、`stm_prevalence`；写入 `project_name`、`output_dir`。
- 错误反馈：未选择目录时提示；部分导出失败会汇总到完成弹窗中。

## Tauri 前端必须迁移的页面能力

- 主导航和流程状态：导入、清洗、LDA、STM、对比、导出入口；根据 `step_imported`、`step_merged`、`step_cleaned`、`step_lda_done`、`step_stm_done` 控制可用性和完成状态。
- 文件导入体验：元数据表和文本表选择、文件格式校验、字段识别展示、缺失字段提示、数据预览、合并结果摘要。
- 清洗配置体验：基础清洗开关、文本长度、文档频率、停用词编辑、停用词文件、自定义词典、原文/清洗后/分词预览、清洗统计。
- LDA 建模体验：参数配置、文类筛选、训练阶段提示、Coherence、主题关键词、文档主题分布表、主题图表、pyLDAvis 打开或生成入口。
- STM 建模体验：R 环境检查、R 安装失败详情、文类筛选、可用协变量分析、prevalence/content 配置、训练状态、主题结果、文档主题表、prevalence 图表。
- 对比分析体验：模型选择、维度筛选、横纵轴选择、柱状图/折线图切换、代表文章列表、原文查看、当前图表导出。
- 批量导出体验：导出目录、可导出项目清单、项目名、导出结果摘要、失败项目详情、处理日志流。

## Tauri 前端需要承载或展示的状态字段

- 数据导入：`metadata_df`、`text_df`、`merged_df`、`unmatched_meta`、`unmatched_text`、`meta_col_map`、`text_col_map`。
- 清洗分词：`cleaned_df`、`tokens_list`、`stopwords`、`stopwords_path`、`custom_dict_path`。
- LDA：`lda_topics`、`lda_doc_topics`、`lda_coherence`，必要时后端保留 `lda_model`、`lda_dictionary`、`lda_corpus`。
- STM：`r_available`、`stm_topics`、`stm_doc_topics`、`stm_prevalence`，必要时后端保留 `stm_result`。
- 会话配置：`project_name`、`output_dir`。
- 流程进度：`step_imported`、`step_merged`、`step_cleaned`、`step_lda_done`、`step_stm_done`。

## 必须迁移的错误和任务反馈

- 输入校验错误：不支持的文件格式、无法解码 CSV、Excel 无工作表、缺少元数据或文本 `doc_id`、缺少正文 `text`。
- 前置条件错误：未合并就清洗、未分词就训练 LDA/STM、筛选文类后无可建模文档、无图表时导出图表。
- 长任务状态：清洗、LDA 训练和 STM 训练必须暴露 `idle/running/succeeded/failed`、阶段文案、完成摘要和错误详情。
- 环境错误：jieba、gensim、pyLDAvis、matplotlib、opencc、rpy2、R 和 R stm 包缺失时，需要返回用户可理解的安装或降级提示。
- 导出错误：单项导出失败不应掩盖其他成功项，前端需要展示成功文件列表和失败原因列表。

## 应继续复用的 Python 能力

- `services/data_service.py`：保留文件读取、多编码 CSV 处理、Excel 首个工作表读取、字段识别、标准化、日期解析、表合并和未匹配记录计算。
- `services/clean_service.py`：保留 `CleanOptions`、OCR 噪声清理、繁简转换、标点和数字过滤、jieba 分词、停用词加载和默认停用词。
- `services/lda_service.py`：保留语料构建、gensim LDA 训练、主题词提取、文档主题分布、Coherence、pyLDAvis 生成和 LDA 结果导出。
- `services/stm_service.py`：保留 R/rpy2 环境检测、R 数据转换、STM 训练、公式字段校验、主题词提取、文档主题分布、prevalence 估计和 STM 结果导出。
- `models/app_state.py`：迁移期可继续作为 Python 进程内会话状态源；Tauri 集成层需要把其中 DataFrame 和模型对象转换为前端可消费的摘要、表格或文件路径。
- `utils/field_mapper.py`、`utils/logger.py`、`utils/mpl_font.py`：继续复用字段映射、日志信号/日志格式和中文绘图字体设置。

## 迁移边界建议

- Tauri 前端负责页面布局、控件状态、用户输入、任务状态展示、结果表格和图表交互。
- Python 层负责文件解析、DataFrame 处理、清洗分词、LDA/STM 训练、结果导出和依赖环境检测。
- 不把 pandas DataFrame、gensim 模型或 rpy2 对象直接暴露给前端；前端只接收序列化摘要、分页表格数据、图表数据、导出路径和错误对象。
- 对比分析中的 `build_topic_summary` 目前在页面内，后续宜迁入服务或集成层，避免 Tauri 前端重新实现 pandas 聚合语义。
- 导出页目前直接写文件，后续宜抽成统一 export service，使 Tauri 与 PySide6 迁移期可共享同一导出语义。
