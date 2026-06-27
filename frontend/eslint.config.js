// AIGameWorld 前端 ESLint 配置 / Frontend ESLint Config
export default [
  {
    languageOptions: {
      ecmaVersion: 2022,          // ES2022 语法 / ES2022 syntax
      sourceType: "module",       // ES Module 模式
    },
    rules: {
      "no-unused-vars": "warn",   // 未使用变量警告 / Warn unused vars
      "no-console": "off",        // 允许 console / Allow console
    },
  },
];
