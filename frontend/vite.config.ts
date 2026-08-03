/** Vite 开发配置 / Vite dev configuration */
import { defineConfig } from "vite";

export default defineConfig({
  server: {
    // 前端开发服务器端口 / Frontend dev server port
    port: 5173,
    open: true,
    // 代理 /api 到后端服务 / Proxy /api to backend service
    // 后端启动需加载 BGE-M3 + 重建 chroma 集合（约 15-20s），
    // 未就绪时 vite 默认直接 ECONNREFUSED→501，这里加容错。
    proxy: {
      "/api": {
        target: "http://localhost:8000",
        changeOrigin: true,
        timeout: 60000,
        proxyTimeout: 60000,
        configure: (proxy) => {
          // 后端未就绪时静默重试，避免向前端抛 501
          proxy.on("error", (err, _req, res) => {
            if (res && typeof res.writeHead === "function" && !res.headersSent) {
              res.writeHead(502, { "Content-Type": "application/json" });
              res.end(JSON.stringify({ error: "backend_not_ready", detail: String(err.message) }));
            }
            // 不打断 vite，仅记录
            console.warn("[vite.proxy] backend not ready:", err.message);
          });
        },
      },
    },
  },
  build: {
    // 构建目标 / Build target
    target: "es2022",
    // 输出目录 / Output directory
    outDir: "dist",
  },
});
