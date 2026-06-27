// SimGameWorld 前端 Vite 配置 / Frontend Vite Config
import { defineConfig } from "vite";

export default defineConfig({
  server: {
    port: 3000,       // 开发服务器端口 / Dev server port
    open: true,       // 自动打开浏览器 / Auto open browser
  },
  build: {
    target: "es2022", // ES2022 目标 / ES2022 target
    outDir: "dist",   // 输出目录 / Output directory
  },
});
