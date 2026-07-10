# Tauri 前端工程

这是历史报刊主题分析工具的迁移期 Tauri + 现代前端骨架。现有 PySide6 入口仍保留在项目根目录的 `main.py` 和 `run.bat`，本目录只承载新版桌面界面。

## 技术栈

- Tauri 2
- Vite
- React
- TypeScript
- Zustand
- lucide-react

## 本地开发

需要先安装 Node.js、Rust 和 Tauri 所需系统依赖。

```bash
npm install
npm run tauri dev
```

仅预览前端界面：

```bash
npm run dev
```

## 目录说明

```text
desktop/
├── src/                 # 现代前端界面
│   ├── App.tsx          # 主布局、导航和页面占位
│   ├── routes.tsx       # 页面路由元数据
│   └── state/           # 前端状态管理
└── src-tauri/           # Tauri 桌面壳配置
```

后续 Task 4/5 会在当前骨架上补齐页面原型，并按既定 JSON Lines bridge 接入 Python 计算层。
