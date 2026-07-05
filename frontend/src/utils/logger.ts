/** 前端日志模块 / Frontend logger module
 *
 * 级别由 CONFIG.LOG.level 控制 / Level controlled by CONFIG.LOG.level
 *   开发默认 debug，生产默认 warn
 *   环境变量: VITE_LOG_LEVEL=debug|info|warn|error|off
 *   运行时: Logger.level = "info" 动态切换
 *
 * 用法:
 *   import { createLogger } from "../utils/logger";
 *   const log = createLogger("Boot");
 *   log.info("loading", { scenes: 3 });
 *
 * 格式: HH:MM:SS.mmm [ModuleName] message
 */

import { CONFIG, type LogLevel } from "../config";

const LEVELS: Record<LogLevel, number> = { debug: 0, info: 1, warn: 2, error: 3, off: 99 };

export const Logger = {
  get level(): LogLevel {
    return CONFIG.LOG.level;
  },
  set level(lv: LogLevel) {
    (CONFIG.LOG as any).level = lv;
  },
};

export interface FrontendLogger {
  debug(msg: string, ...args: unknown[]): void;
  info(msg: string, ...args: unknown[]): void;
  warn(msg: string, ...args: unknown[]): void;
  error(msg: string, ...args: unknown[]): void;
}

export function createLogger(module: string): FrontendLogger {
  const prefix = `[${module}]`;

  const logAt = (lv: LogLevel, fn: (...args: unknown[]) => void, msg: string, ...args: unknown[]) => {
    if (LEVELS[lv] < LEVELS[CONFIG.LOG.level]) return;
    const ts = new Date().toISOString().slice(11, 23);
    fn(`${ts} ${prefix} ${msg}`, ...args);
  };

  return {
    debug: (msg, ...args) => logAt("debug", console.debug, msg, ...args),
    info: (msg, ...args) => logAt("info", console.log, msg, ...args),
    warn: (msg, ...args) => logAt("warn", console.warn, msg, ...args),
    error: (msg, ...args) => logAt("error", console.error, msg, ...args),
  };
}
