# Tasks
- [x] Task 1: 梳理现有 PySide6 GUI 的业务流程和可复用边界。
  - [x] SubTask 1.1: 检查 `gui/pages/*.py` 中导入、清洗、LDA、STM、对比和导出的用户流程。
  - [x] SubTask 1.2: 标记必须迁移到 Tauri 前端的页面能力、状态字段和错误反馈。
  - [x] SubTask 1.3: 标记应继续复用的 `services/*.py` 和 `models/app_state.py` 能力。

- [x] Task 2: 设计 Tauri 前端与 Python 计算层的本地集成边界。
  - [x] SubTask 2.1: 明确前端需要的导入、清洗、LDA、STM、对比、导出 API 或命令契约。
  - [x] SubTask 2.2: 设计任务状态、进度、错误和结果摘要的数据结构。
  - [x] SubTask 2.3: 选择最小可落地的本地调用方式，优先保证开发调试简单和 Python 逻辑可复用。

- [x] Task 3: 初始化 Tauri + 现代前端工程骨架。
  - [x] SubTask 3.1: 新建前端桌面应用目录和 Tauri 基础配置。
  - [x] SubTask 3.2: 建立主布局、导航、页面路由和基础状态管理。
  - [x] SubTask 3.3: 保留现有 PySide6 入口，不删除旧 GUI 文件。

- [x] Task 4: 实现新版 GUI 的核心工作流页面原型。
  - [x] SubTask 4.1: 实现导入页、清洗页和分析页的现代化布局与主操作流。
  - [x] SubTask 4.2: 实现对比页和导出页的结果查看与导出入口。
  - [x] SubTask 4.3: 为长任务接入忙碌状态、阶段提示、完成状态和错误展示。

- [x] Task 5: 接入 Python 后端能力并验证功能不回退。
  - [x] SubTask 5.1: 将前端命令连接到 Python 数据导入、清洗、LDA、STM 和导出能力。
  - [x] SubTask 5.2: 验证现有 PySide6 入口仍可作为迁移期回退路径。
  - [x] SubTask 5.3: 运行可用测试、构建或静态检查；如环境缺失，记录阻塞原因。

## Task 5 验证记录
- 已新增 `backend.bridge` JSON 命令入口，Tauri `run_python_task` 命令通过本地 Python 调用导入、清洗、LDA、STM 检查、对比和导出任务。
- 已验证 `python -m backend.bridge task.import` 与 `python -m backend.bridge task.clean` 可返回成功 JSON 状态。
- 已验证 `python -c "import main; print('pyside-entry-ok')"` 成功，现有 PySide6 入口仍可作为迁移期回退路径。
- 已验证 `python -m py_compile backend\bridge.py main.py` 成功，编辑器诊断未发现新增错误。
- 该记录中的 `gensim`、`rpy2`、`npm` 和 `cargo` 环境阻塞已在 Task 6 中补齐并验证通过；当前保留为历史上下文，不再作为未完成项。

## 2026-07-03 清单复核修复任务
- [x] Task 6: 补齐 Tauri GUI 迁移的本机依赖、资源和构建验证。
  - [x] SubTask 6.1: 安装或暴露 Node.js/npm 到 PATH，重跑 `npm run build` 验证 React/Vite 前端构建。
  - [x] SubTask 6.2: 安装或暴露 Rust/Cargo 到 PATH，重跑 `cargo check` 验证 Tauri Rust 壳。
  - [x] SubTask 6.3: 修复 `desktop/src/App.tsx` 类型边界，使 `welcome` 路由不再索引工作流页面配置。
  - [x] SubTask 6.4: 补齐 `desktop/src-tauri/icons/icon.ico`，解除 Tauri Windows 资源生成阻塞。
  - [x] SubTask 6.5: 使用项目 `.venv` 重跑 `backend.bridge` 的导入、清洗、LDA、STM 环境检查和导出任务。

## 2026-07-04 恢复进度记录
- 已确认当前环境 `node --version` 返回 `v22.16.0`，`npm --version` 返回 `10.9.4`。
- 已运行 `npm run build`，React/Vite 前端构建成功。
- 已确认当前环境 `cargo --version` 返回 `cargo 1.96.1 (356927216 2026-06-26)`。
- 已运行 `cargo check`，Tauri Rust 壳检查成功。
- 已修复 `desktop/src/App.tsx` 的 TypeScript 类型错误：工作流页面路由收窄为不含 `welcome`，页面配置类型改为 `PageDefinition`，图标节点类型改为 `ReactNode`。
- 已新增 `desktop/src-tauri/icons/icon.ico` 占位图标；首次 PNG 内嵌 ICO 因 CRC 解码失败，已替换为合法 BMP/DIB ICO，`cargo check` 通过。
- 已运行 `.venv\Scripts\python.exe --version`，项目虚拟环境为 `Python 3.12.10`。
- 已运行 `.venv\Scripts\python.exe -m pip check`，未发现 Python 依赖冲突。
- 已验证 `.venv` 中 `PySide6`、`pandas`、`numpy`、`openpyxl`、`xlrd`、`jieba`、`gensim`、`matplotlib`、`pyLDAvis`、`rpy2`、`opencc` 均可导入。
- 已运行 `.venv\Scripts\python.exe -m backend.bridge task.import`，导入与合并返回成功 JSON，样例数据合并 6 篇。
- 已运行 `.venv\Scripts\python.exe -m backend.bridge task.clean`，清洗分词返回成功 JSON，有效语料 6 篇、词元 53 个、唯一词 33 个。
- 已运行 `.venv\Scripts\python.exe -m backend.bridge task.lda`，LDA 训练返回成功 JSON，主题数 3，Coherence 为 0.47489835130307917。
- 已运行 `.venv\Scripts\python.exe -m backend.bridge task.stm`，STM 环境检查返回成功 JSON，R 环境可用，输出中仍出现一条 Windows 下 `sh` 不存在的外部提示，需后续清理诊断输出。
- 已运行 `.venv\Scripts\python.exe -m backend.bridge task.export`，导出返回成功 JSON，共导出 7 个文件到临时输出目录。

## 2026-07-04 下一阶段任务
- [ ] Task 7: 将迁移期原型推进到可交付桌面应用验证。
  - [ ] SubTask 7.1: 用真实用户样例数据替换 bridge 内置样例，验证导入、清洗、LDA 和导出结果的字段、行数与旧 PySide6 流程一致。
  - [x] SubTask 7.2: 清理 STM 环境检查中的 Windows `sh` 外部提示，保证 stdout 只输出可解析 JSON 或明确分离诊断日志。
  - [x] SubTask 7.3: 将 `desktop/src-tauri/icons/icon.ico` 占位图标替换为正式应用图标，并补齐 Tauri bundle 需要的多尺寸图标资源。
  - [x] SubTask 7.4: 运行 `npm run tauri build` 或等价打包命令，验证 Windows 桌面安装包/可执行文件生成。

## 2026-07-04 Task 7 执行记录
- 已扫描仓库内 `.csv`、`.xlsx`、`.xls`，未发现可用于 Task 7.1 的真实报刊业务样例数据；`.venv` 中第三方库样例数据不适合验证旧 PySide6 流程一致性。Task 7.1 需等待用户提供可通过 `doc_id` 关联的元数据表和正文表。
- 已修改 `backend.bridge`，在 STM 环境检查期间将底层 stdout 诊断重定向到 stderr；已验证 `.venv\Scripts\python.exe -m backend.bridge task.stm 1> stdout 2> stderr` 后 stdout 只包含 JSON，Windows `sh` 提示被分离到 stderr。
- 已修改 Tauri Rust 层 `run_python_task`，从 Python stdout 最后一条非空行解析 JSON，提高对第三方环境诊断噪声的容错性。
- 已生成 `desktop/src-tauri/icons/32x32.png`、`128x128.png`、`128x128@2x.png`、`256x256.png` 和多尺寸 `icon.ico`，并更新 `tauri.conf.json` 的 bundle icon 配置。
- 已运行 `npm.cmd run build`，React/Vite production 构建成功；直接运行 `npm run build` 仍会被 PowerShell `npm.ps1` 执行策略拦截，验证继续使用 `npm.cmd`。
- 已运行 `cargo check --manifest-path desktop\src-tauri\Cargo.toml`；一次增量编译触发 `rustc 1.96.1` 内部崩溃，设置 `CARGO_INCREMENTAL=0` 后检查通过。
- 已运行 `$env:CARGO_INCREMENTAL='0'; npm.cmd run tauri build`，release 可执行文件生成成功：`desktop\src-tauri\target\release\topic-analyzer-desktop.exe`，大小约 10.6 MB；当前未发现 `target\release\bundle` 安装包产物。
- 编辑器诊断未发现新增错误。

## 2026-07-04 新版 GUI 修正任务
- [x] Task 8: 完成新版 GUI 交付前体验修正并对照 PySide6 主流程。
  - [x] SubTask 8.1: 清理新版界面中的迁移期文案、底部迁移标签和原型状态提示。
  - [x] SubTask 8.2: 用正式程序 logo 图形替换左上角文字“史”，并保留清晰应用品牌名。
  - [x] SubTask 8.3: 对照 PySide6 导入页，补齐元数据表、正文表、关联字段选择、字段识别结果和合并预览区域。
  - [x] SubTask 8.4: 将导入页选择的元数据路径、正文路径和关联字段传入 Python bridge，并支持覆盖 doc_id 字段映射。
  - [x] SubTask 8.5: 运行前端构建、Python bridge 导入验证和编辑器诊断，记录结果。

## 2026-07-04 Task 8 验证记录
- 已运行 `npm.cmd run build`，TypeScript 与 Vite production 构建成功。
- 已运行 `.venv\Scripts\python.exe -m py_compile backend\bridge.py`，Python bridge 语法检查通过。
- 已运行 `.venv\Scripts\python.exe -m backend.bridge task.import`，样例导入返回成功 JSON，元数据 6 行、正文 6 行、合并 6 篇、未匹配 0 条。
- 已通过 `backend.bridge.handle('task.import', {'metadataIdField': 'doc_id', 'textIdField': 'doc_id'})` 验证新增关联字段载荷可正常导入合并；直接 CLI 传 JSON 时 PowerShell 包装会破坏引号，属于命令转义问题。
- 已扫描新版前端源码，未发现 `迁移期`、`原型`、`Tauri Desktop`、`migration-panel`、`completion-row` 或左上角文字“史”的残留。
- 编辑器诊断未发现新增错误。

## 2026-07-04 Release 同步任务
- [x] Task 9: 同步新版 GUI release 构建产物状态。
  - [x] SubTask 9.1: 运行 `$env:CARGO_INCREMENTAL='0'; npm.cmd run tauri build`，确认 Tauri release 构建成功。
  - [x] SubTask 9.2: 核对 `desktop\src-tauri\target\release\topic-analyzer-desktop.exe` 的更新时间和大小。
  - [x] SubTask 9.3: 更新 `tasks.md` 与 `checklist.md` 的 release 同步记录。

## 2026-07-04 Task 9 验证记录
- 已在 `desktop` 目录运行 `$env:CARGO_INCREMENTAL='0'; npm.cmd run tauri build`，命令退出码为 0，前端 production 构建与 Tauri release 编译成功。
- 已核对 release 可执行文件：`desktop\src-tauri\target\release\topic-analyzer-desktop.exe`，更新时间为 2026/7/4 22:45:55，本地时区为 Asia/Shanghai；文件大小为 10,718,208 字节。
- 已检查 `desktop\src-tauri\target\release\bundle`，当前未发现安装包产物。

## 2026-07-04 release 运行时 Python bridge 修复任务
- [x] Task 10: 修复 release exe 调用 Python bridge 时 `ModuleNotFoundError: No module named 'pandas'`。
  - [x] SubTask 10.1: 修改 `desktop/src-tauri/src/lib.rs` 的 `run_python_task`，优先使用项目根目录下的 `.venv\Scripts\python.exe`，其次 `TOPIC_ANALYZER_PYTHON` 环境变量，最后回退 `python`。
  - [x] SubTask 10.2: 重新运行 `tauri build` 并核对 release 可执行文件更新。

## 2026-07-04 Task 10 验证记录
- 已修改 `desktop/src-tauri/src/lib.rs`：当 `<project_root>/.venv/Scripts/python.exe` 存在时优先使用它，确保 release exe 运行时能找到 `pandas`、`gensim` 等项目虚拟环境依赖。
- 已在 `desktop` 目录运行 `$env:CARGO_INCREMENTAL='0'; npm.cmd run tauri build`，命令退出码为 0，release 重新编译成功。
- 已核对 release 可执行文件：`desktop\src-tauri\target\release\topic-analyzer-desktop.exe`，更新时间为 2026/7/4 23:26:53，文件大小为 10,807,296 字节。

## 2026-07-10 接手后重新规划

### 当前判断
- 已完成的 Task 1-10 证明新版 Tauri 壳、Python bridge、构建链路和 release exe 都能跑通。
- 仍不能把新版 GUI 视为完整可交付版本：当前 bridge 由 Tauri 每次启动独立 Python 进程，且 `backend.bridge.handle()` 会重置 `AppState`，导致导入后的真实文件状态不能自然传递到清洗、LDA、对比和导出任务；下游命令可能回退到内置样例数据。
- PySide6 旧 GUI 仍是完整业务回退路径；Tauri 新 GUI 下一阶段重点不是继续做静态页面，而是补齐真实会话状态、结果查询、真实数据一致性验证和交付形态。
- 原 Task 7.1 保留为历史未完成项，但实际验收工作并入 Task 17 统一处理。

### Phase A: 稳定工程基线
- [x] Task 11: 让测试和基础健康检查稳定可重复。
  - [x] SubTask 11.1: 补齐测试运行入口，明确 `pytest` 是开发依赖还是项目依赖，并使 `.venv\Scripts\python.exe -m pytest -q` 可运行。
  - [x] SubTask 11.2: 修复或重定 `build_topic_summary` 的排序契约，使 [tests/test_analysis_enhancements.py](tests/test_analysis_enhancements.py) 与 [gui/pages/compare_page.py](gui/pages/compare_page.py) 行为一致。
  - [x] SubTask 11.3: 清理 [services/clean_service.py](services/clean_service.py) 的正则 `SyntaxWarning`，避免后续 Python 版本升级时变成隐性问题。
  - [x] SubTask 11.4: 固化本机验证命令清单：Python 编译检查、pytest、`npm.cmd run build`、`cargo check --manifest-path desktop\src-tauri\Cargo.toml`。

  验证记录（2026-07-10）：`.venv\Scripts\python.exe -m py_compile backend\bridge.py main.py services\clean_service.py gui\pages\compare_page.py`、`.venv\Scripts\python.exe -m pytest -q`（5 passed）、`npm.cmd run build`、`cargo check --manifest-path src-tauri\Cargo.toml` 均通过。

- [x] Task 12: 修复 Tauri 到 Python 的真实会话状态链路。
  - [x] SubTask 12.1: 明确 bridge 状态策略：常驻 Python bridge、会话文件缓存，或每个任务显式传入完整上游输入；优先选择实现简单且能支持真实文件连续工作流的方案。
  - [x] SubTask 12.2: 移除或改造 `handle()` 内的无条件 `reset_state()`，让 `task.import -> task.clean -> task.lda -> task.compare -> task.export` 能围绕同一项目状态执行。
  - [x] SubTask 12.3: 为真实文件路径、字段映射、清洗参数、LDA 参数和输出目录建立可序列化 session payload，避免下游任务隐式使用内置样例数据。
  - [x] SubTask 12.4: 增加 bridge 级顺序调用测试，覆盖导入真实/临时 CSV、清洗、LDA 和导出，并校验行数与导出文件。

  验证记录（2026-07-10）：采用 Tauri 常驻 Rust 进程内 JSON session payload 的方案；新导入才重置 bridge 状态。`tests/test_bridge_session.py` 模拟每一步均由新 bridge 进程执行，验证真实 CSV 的合并行数、清洗文档数、LDA 主题数及导出文件，并验证缺少导入会话时会显式报错。

### Phase B: 补齐新版 GUI 的真实结果能力
- [ ] Task 13: 扩展 Python bridge 命令契约到结果查询和分页预览。
  - [ ] SubTask 13.1: 实现 `table.preview`，支持 metadata、text、merged、cleaned、ldaDocTopics、stmDocTopics 的分页 JSON 返回。
  - [ ] SubTask 13.2: 实现 `clean.preview`、`lda.get_result`、`stm.analyze_covariates`、`compare.build_summary`、`export.list_items` 的最小可用版本。
  - [ ] SubTask 13.3: 统一 bridge 错误结构和错误码，前端展示 `message`、`suggestion` 和可展开诊断详情。
  - [ ] SubTask 13.4: 将对比聚合与批量导出中仍散落在 PySide 页面内的逻辑下沉到 service 或 backend 命令层。

- [ ] Task 14: 把 Tauri 页面从摘要原型推进到真实数据界面。
  - [ ] SubTask 14.1: 导入页展示真实字段识别、未匹配记录摘要和真实合并预览，不再使用固定样例表格。
  - [ ] SubTask 14.2: 清洗页接入真实清洗参数、停用词/自定义词典输入、清洗预览和清洗后分页结果。
  - [ ] SubTask 14.3: LDA 页接入主题数、passes、iterations、文类筛选等真实控件，并展示主题词、Coherence 和文档主题表。
  - [ ] SubTask 14.4: 对比页展示真实聚合图表数据、代表文章和原文查看。
  - [ ] SubTask 14.5: 导出页展示真实可导出项目、缺失原因、成功文件和部分失败原因。

- [ ] Task 15: 完成 STM 在新版 GUI 中的真实训练闭环。
  - [ ] SubTask 15.1: 将 `task.stm` 从“环境检查”升级为可选择“检查 R 环境”或“训练 STM”的明确任务。
  - [ ] SubTask 15.2: 接入 prevalence 公式、content 协变量、文类筛选、主题数、EM 迭代和随机种子。
  - [ ] SubTask 15.3: 返回 STM 主题词、文档主题分布和 prevalence 摘要，并支持导出。
  - [ ] SubTask 15.4: 对 R/rpy2/stm 缺失、公式字段不可用、空训练集等错误给出可操作提示。

- [ ] Task 16: 整理服务层边界，减少 PySide 与 Tauri 双实现。
  - [ ] SubTask 16.1: 新增或整理 `services/compare_service.py`，承接 `build_topic_summary`、代表文章筛选和图表数据结构。
  - [ ] SubTask 16.2: 新增或整理 `services/export_service.py`，统一合并数据、清洗语料、LDA、STM 和 session 配置导出语义。
  - [ ] SubTask 16.3: 让 PySide6 页面和 Tauri bridge 尽量复用同一 service，避免结果口径分叉。

### Phase C: 真实数据验收与交付
- [ ] Task 17: 用真实报刊样例数据做新旧流程一致性验收。
  - [ ] SubTask 17.1: 准备或接收可通过 `doc_id` 关联的元数据表和正文表，覆盖中文字段、英文字段、缺失字段、未匹配记录和跨年月日期。
  - [ ] SubTask 17.2: 对照 PySide6 与 Tauri 的导入行数、字段映射、合并行数、清洗文档数、LDA 主题结果和导出文件。
  - [ ] SubTask 17.3: 建立一套可重复的小样例 fixtures，进入测试或验证脚本，替代 bridge 内置演示数据承担回归职责。
  - [ ] SubTask 17.4: 验证中文编码、路径空格、Windows PowerShell 转义、CSV 多编码和 Excel 首工作表读取。

- [ ] Task 18: 梳理 release 分发形态并完成交付 smoke test。
  - [ ] SubTask 18.1: 决定 release 是否依赖项目目录 `.venv`，或改为打包 Python runtime/sidecar；当前 exe 仍依赖项目 `.venv`，不等于独立安装包。
  - [ ] SubTask 18.2: 运行 `npm.cmd run tauri build`，记录 exe、bundle 或安装包产物位置、大小和时间。
  - [ ] SubTask 18.3: 在干净目录做启动、导入样例、清洗、LDA、导出 smoke test。
  - [ ] SubTask 18.4: 更新 README 或发布说明，明确启动方式、依赖、已知限制和回退到 PySide6 的方式。

## 2026-07-03 清单复核记录
- 已确认 `desktop/package.json`、`desktop/src-tauri/Cargo.toml` 与 `desktop/src-tauri/tauri.conf.json` 建立了 Tauri + React + Vite 工程骨架。
- 已确认 `desktop/src/routes.tsx` 和 `desktop/src/App.tsx` 覆盖导入、清洗、LDA、STM、对比和导出入口。
- 已确认 `desktop/src-tauri/src/lib.rs` 的 `run_python_task` 与 `backend/bridge.py` 的 JSON 响应形成本地调用契约。
- 已确认 `desktop/src/state/workflowStore.ts` 为长任务提供 running、succeeded、failed、phase、progress、summary 和 error 状态。
- 已运行 `python -m backend.bridge task.import`、`python -m backend.bridge task.clean`、`python -m py_compile backend\bridge.py main.py` 和 `python -c "import main; print('pyside-entry-ok')"`，均成功。
- 当日记录中的 `gensim`、`rpy2`、`npm` 和 `cargo` 阻塞已被 2026-07-04 的 `.venv`、`npm run build` 与 `cargo check` 验证覆盖；当前不再作为 Task 6 阻塞项。

# Task Dependencies
- Task 2 depends on Task 1
- Task 3 depends on Task 2
- Task 4 depends on Task 3
- Task 5 depends on Task 4
- Task 6 depends on Task 5
- Task 7 depends on Task 6
- Task 8 depends on Task 7
- Task 9 depends on Task 8
- Task 10 depends on Task 9
- Task 11 depends on Task 10
- Task 12 depends on Task 11
- Task 13 depends on Task 12
- Task 14 depends on Task 13
- Task 15 depends on Task 13
- Task 16 depends on Task 13
- Task 17 depends on Task 14, Task 15, and Task 16
- Task 18 depends on Task 17
