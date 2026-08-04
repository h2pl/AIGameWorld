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
  },
});
