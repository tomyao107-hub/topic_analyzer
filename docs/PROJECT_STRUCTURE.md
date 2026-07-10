# 项目结构说明

这个项目现在按“源码、桌面壳、测试、文档、可重建产物”来区分。

## 保留在项目中的内容

- `main.py`：冻结的 PySide6 v1 旧界面入口。
- `run.bat`：Tauri v2 默认启动脚本；`run-legacy.bat` 启动旧 PySide6 回退界面。
- `requirements.txt` / `requirements-dev.txt`：Python 运行和开发验证依赖。
- `backend/`：Tauri 桌面壳与 Python 业务逻辑之间的桥接层。
- `models/`：应用状态模型。
- `services/`：数据导入、清洗、LDA、STM、对比分析、导出等业务服务。
- `gui/`：PySide6 界面代码。
- `utils/`：字段映射、日志、字体等辅助工具。
- `tests/`：自动化测试。
- `desktop/`：React + Tauri 桌面壳源码。
- `docs/dev-history/`：从旧开发环境保留下来的规格、审计和任务记录。

## 不应提交或长期保留的内容

这些目录和文件都是可重建的，已经写入根目录 `.gitignore`：

- `.venv/`
- `__pycache__/`
- `.pytest_cache/`
- `.uploads/`
- `desktop/node_modules/`
- `desktop/dist/`
- `desktop/src-tauri/target/`
- `desktop/src-tauri/gen/`

## 重新生成本地环境

Tauri v2 桌面应用：

```bat
run.bat
```

PySide6 v1 回退：

```bat
run-legacy.bat
```

开发验证：

```bat
.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
.venv\Scripts\python.exe -m pytest -q
```

Tauri / React 桌面壳：

```bat
cd desktop
npm install
npm run build
cargo check --manifest-path src-tauri\Cargo.toml
```
