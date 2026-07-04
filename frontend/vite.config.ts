/** Vite 开发配置 / Vite dev configuration */
import { defineConfig } from "vite";

export default defineConfig({
  server: {
    // 前端开发服务器端口 / Frontend dev server port
    port: 5173,
    open: true,
    // 代理 /api 到后端服务 / Proxy /api to backend service
    proxy: {
      "/api": "http://localhost:3003",
    },
  },
  build: {
    // 构建目标 / Build target
    target: "es2022",
    // 输出目录 / Output directory
    outDir: "dist",
  },
});
