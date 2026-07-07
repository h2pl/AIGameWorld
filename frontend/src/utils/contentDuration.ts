/** 展示时长计算 / Content display duration — 按文本长度自适应，统一入口 */

/** @param text 展示的完整内容 / Full content text
 *  @param minMs 最小停留毫秒（默认 1000） / Minimum dwell ms (default 1000)
 *  @returns 停留毫秒数 / Dwell duration in ms
 */
export function contentDuration(text: string, minMs = 1000): number {
  // 中文 ~350字/分钟阅读速度，基准 msPerChar / Based on ~350 chars/min reading speed
  const chars = Math.max(text.length, 1);
  return Math.max(minMs, minMs + chars * 20);
}

/** 最短停留时间 / Minimum dwell time constant */
export const CONTENT_DWELL_MIN_MS = 1000;
