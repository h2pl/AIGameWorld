/** Vitest 测试配置 / Vitest test configuration */
import { defineConfig } from "vitest/config";

export default defineConfig({
  test: {
    // 使用 jsdom 模拟浏览器环境 / Use jsdom to simulate browser environment
    environment: "jsdom",
    // 全局导入测试 API / Global test APIs (describe, it, expect)
    globals: true,
    // 测试文件匹配模式 / Test file patterns
    include: ["tests/**/*.test.ts"],
    // 全局 setup：桩 HTMLCanvasElement.getContext，避免 Phaser 在 node 下崩溃
    setupFiles: ["tests/setup.ts"],
  },
  // 强制 Phaser 解析到打包后的 dist（vitest 默认可能解析到 src 导致 WebGL 模块缺失）
  resolve: {
    alias: {
      phaser: "phaser/dist/phaser.js",
    },
  },
});
