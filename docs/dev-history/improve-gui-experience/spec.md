# Tauri GUI界面体验升级 Spec

## Why
当前应用已具备完整的数据导入、清洗、建模、对比和导出流程，但 PySide6 Widgets 的现代视觉表现、动效能力和复杂交互体验存在上限。引入 Tauri + 现代前端作为新的界面层，可以显著提升设计感和操作流畅度，同时继续复用现有 Python 数据处理与建模能力。

## What Changes
- 新增 Tauri 桌面壳和现代前端界面，作为后续 GUI 的目标体验方向。
- 保留现有 Python services 的核心数据处理、LDA、STM、对比和导出能力。
- 为 Python 计算层设计清晰的本地调用边界，使前端可以触发导入、清洗、建模、查询状态和导出。
- 重新设计导入、清洗、LDA、STM、对比和导出工作流，让页面结构、操作反馈和长任务状态更符合现代数据分析工具体验。
- 在迁移阶段允许 PySide6 版本继续作为旧 GUI 入口，避免一次性重写导致功能不可用。
- 不改变现有输入数据格式、建模算法和导出文件语义。

## Impact
- Affected specs: GUI 主框架、前端工作流、本地 Python 调用边界、任务状态反馈、桌面打包方式。
- Affected code: 新增 Tauri/前端工程、Python 本地服务适配层、现有 `services/*.py`、`models/app_state.py`，迁移阶段参考 `gui/pages/*.py` 的业务流程。

## ADDED Requirements
### Requirement: Tauri现代桌面界面
The system SHALL provide a Tauri-based desktop GUI with a modern frontend implementation for the historical newspaper topic analysis workflow.

#### Scenario: 用户启动新界面
- **WHEN** 用户启动新的 Tauri 桌面应用
- **THEN** 系统应展示现代化主界面，并能进入导入、清洗、LDA、STM、对比和导出流程

### Requirement: Python计算能力复用
The system SHALL reuse the existing Python data processing, cleaning, LDA, STM, comparison, and export logic through a stable local integration boundary.

#### Scenario: 前端触发清洗任务
- **WHEN** 用户在 Tauri 前端启动文本清洗
- **THEN** 系统应调用 Python 清洗能力并返回任务状态、统计结果和错误信息

### Requirement: 流程状态清晰可见
The system SHALL make the current workflow state and next available actions visually clear.

#### Scenario: 用户完成数据导入
- **WHEN** 用户成功导入并合并数据
- **THEN** 前端导航、页面状态区和主操作按钮应同步展示已完成状态，并明确后续可执行步骤

### Requirement: 耗时操作反馈流畅
The system SHALL provide responsive feedback for long-running operations without freezing or confusing the user.

#### Scenario: 用户开始清洗或建模
- **WHEN** 用户启动清洗、LDA 或 STM 训练
- **THEN** 前端应展示忙碌状态、进度或阶段提示、完成结果和失败信息，并在任务结束后恢复可操作状态

### Requirement: 页面操作区更易用
The system SHALL organize each page around the primary task, with secondary controls visually separated from primary actions.

#### Scenario: 用户进入分析页面
- **WHEN** 用户进入 LDA 或 STM 页面
- **THEN** 参数设置、启动按钮、结果摘要、图表区域和代表文章区域应清晰分区，避免用户在密集控件中迷失

### Requirement: 渐进迁移兼容性
The system SHALL allow the existing PySide6 application to remain available during the Tauri migration until the new GUI covers the required workflow.

#### Scenario: 新界面未覆盖全部能力
- **WHEN** Tauri GUI 尚未完成某个页面能力
- **THEN** 现有 PySide6 入口仍应可作为功能回退路径

## MODIFIED Requirements
### Requirement: 主窗口页面承载能力
The new Tauri shell SHALL replace the long-term GUI host role of the current PySide6 stacked-page window, while preserving equivalent workflow coverage and user-visible capabilities.

### Requirement: 现有业务流程
The import, clean, LDA, STM, compare, and export workflows SHALL retain their current data inputs, outputs, and core processing behavior while moving interaction and presentation to the Tauri frontend.

## REMOVED Requirements
无。
