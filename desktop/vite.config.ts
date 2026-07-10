import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],
  clearScreen: false,
  server: {
    port: 1420,
    strictPort: true,
    // Cargo 会在 src-tauri/target 中不断创建并锁定 Windows 可执行文件。
    // Vite 不需要观察 Rust 源码或构建产物；排除整个目录可避免 Node 24
    // 在尝试 watch 被 Cargo 占用的 .exe 时抛出 EBUSY。
    watch: {
      ignored: ["**/src-tauri/**"]
    }
  },
  envPrefix: ["VITE_", "TAURI_"]
});
