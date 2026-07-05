// AIGameWorld 前端 ESLint 配置 / Frontend ESLint Config
import tsParser from "@typescript-eslint/parser";
import tsPlugin from "@typescript-eslint/eslint-plugin";

export default [
  {
    files: ["src/**/*.ts", "tests/**/*.ts"], // 匹配源码与测试 / Match source and test files
    languageOptions: {
      ecmaVersion: 2022,          // ES2022 语法 / ES2022 syntax
      sourceType: "module",       // ES Module 模式
      parser: tsParser,           // TypeScript 解析器 / TypeScript parser
    },
    plugins: {
      "@typescript-eslint": tsPlugin,
    },
    rules: {
      "no-unused-vars": "off",                        // 关闭 JS 版本，启用 TS 版本
      "@typescript-eslint/no-unused-vars": "warn",    // 未使用变量警告 / Warn unused vars
      "no-console": "off",                            // 允许 console / Allow console
      "@typescript-eslint/no-explicit-any": "off",    // 允许 any / Allow any
    },
  },
];
