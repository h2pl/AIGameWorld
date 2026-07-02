/** Vite 环境变量声明 / Vite environment variable declarations */
interface ImportMetaEnv {
  /** 可选后端 API 根地址 / Optional backend API base URL */
  readonly VITE_API_BASE_URL?: string;
}

/** ImportMeta 类型扩展 / ImportMeta type augmentation */
interface ImportMeta {
  readonly env: ImportMetaEnv;
}
