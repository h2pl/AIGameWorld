/** 前端配置 / Frontend Configuration — HTTP API（Vite proxy 处理 /api）*/
const DEFAULT_API_ORIGIN = "";
/** API 基础地址 / API base URL */
const API_BASE = (import.meta.env.VITE_API_BASE_URL || DEFAULT_API_ORIGIN).replace(/\/$/, "");

/** 日志级别 / Log level */
export type LogLevel = "debug" | "info" | "warn" | "error" | "off";

/** 全局配置对象 / Global config object */
export const CONFIG = {
  CANVAS: { width: 960, height: 640 },
  TILE: { size: 32 },
  COLOR: {
    background: 0x1a1a2e as number,
    pc_border: 0xffd700 as number,
    pc_color: 0x3498db as number,
    actor_colors: [0xe74c3c, 0x2ecc71, 0xf39c12, 0x9b59b6, 0x1abc9c] as number[],
    text: "#ffffff" as string,
    text_dim: "#8899aa" as string,
  },
  LOG: {
    level: (import.meta.env.VITE_LOG_LEVEL ||
      (import.meta.env.PROD ? "warn" : "debug")) as LogLevel,
  },
  API: { base: API_BASE, health: "/health", worldState: "/api/world" },
};
