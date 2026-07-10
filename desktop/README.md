# Tauri 前端工程

这是历史报刊主题分析工具的 Tauri + React 桌面端。现有 PySide6 入口仍保留在项目根目录的 `main.py` 和 `run.bat`；新版桌面端已接入相同的导入、清洗、LDA、STM、对比和导出服务。

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
│   ├── App.tsx          # 主布局、参数表单和结果视图
│   ├── routes.tsx       # 页面路由元数据
│   └── state/           # 前端状态管理
└── src-tauri/           # Tauri 桌面壳配置
```

Python 计算通过 `backend.bridge` 的 JSON 协议调用。文件选择、停用词加载、输出目录选择和图表 PNG 保存由 Tauri 原生命令提供。
