/** Vite 环境变量声明 / Vite environment variable declarations */
interface ImportMetaEnv {
  /** 可选后端 API 根地址 / Optional backend API base URL */
  readonly VITE_API_BASE_URL?: string;
  /** 日志级别 / Log level */
  readonly VITE_LOG_LEVEL?: string;
  /** Vite 内置：是否生产模式 / Vite built-in: is production */
  readonly PROD: boolean;
  readonly DEV: boolean;
  readonly MODE: string;
}

/** ImportMeta 类型扩展 / ImportMeta type augmentation */
interface ImportMeta {
  readonly env: ImportMetaEnv;
}
