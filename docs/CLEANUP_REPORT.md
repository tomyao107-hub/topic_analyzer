# 整理记录

日期：2026-07-10

## 已整理

- 新增根目录 `.gitignore`，覆盖 Python、pytest、npm、Tauri/Rust、IDE 和本地数据生成物。
- 新增 `docs/PROJECT_STRUCTURE.md`，说明当前项目结构和本地环境重建方式。
- 将旧开发环境记录从 `.trae/specs/improve-gui-experience/` 移到 `docs/dev-history/improve-gui-experience/`。

## 已清理的可重建产物

- `.venv/`
- `.uploads/`
- `__pycache__/` 及源码目录下的 Python 字节码缓存
- `desktop/node_modules/`
- `desktop/dist/`
- `desktop/src-tauri/target/`
- `desktop/src-tauri/gen/`

## 保留的异常残留

- `.pytest_cache/`：该目录读取 ACL、接管所有权和删除都返回 Windows `Access is denied`。当前体积约 0 MB，已被 `.gitignore` 忽略。

## 验证

清理前：

- `.venv\Scripts\python.exe -m pytest -q`：7 passed
- `npm.cmd run build`：通过
- `cargo check --manifest-path desktop\src-tauri\Cargo.toml`：通过

清理后：

- `py -m py_compile main.py backend\bridge.py services\clean_service.py services\compare_service.py services\export_service.py gui\pages\compare_page.py`：通过
