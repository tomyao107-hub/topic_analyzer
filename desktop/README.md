# 历史文献主题分析工具 v2 桌面端

这是 v2 的正式界面，基于 Tauri 2、React、TypeScript 和 Zustand。Python 计算通过 `backend.bridge` 的 `schemaVersion: 2` 会话协议调用。

## 本地开发

```bash
npm install
npm run tauri dev
```

只验证前端：

```bash
npm run build
```

Rust 验证：

```bash
cargo check --manifest-path src-tauri/Cargo.toml
```

## v2 界面能力

- 单一 CSV/Excel 文献表导入与严格错误定位
- 中文/英文独立清洗配置和预览
- 中英文 LDA/STM 配置、状态和结果分别保留
- 动态历史元数据维度与同语言主题比较
- 公共数据 + `zh/`、`en/` 分目录导出

旧 PySide6 界面不属于 v2 功能范围。
