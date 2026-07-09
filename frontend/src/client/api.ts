// -- file start -- / file start
/** HTTP API 层 / HTTP API layer — 纯网络调用，无业务逻辑 */

// ── 链路追踪 / Tracing ──
let _currentTraceId = "";

/** 获取当前 trace_id / Get current trace ID */
export function getCurrentTraceId(): string {
  return _currentTraceId;
}

/** 带 trace 传播的 fetch / Fetch with trace propagation */
async function fetchWithTrace(url: string, options?: RequestInit): Promise<Response> {
  const traceId = _currentTraceId || crypto.randomUUID();
  const resp = await fetch(url, {
    ...options,
    headers: {
      ...options?.headers,
      "X-Trace-Id": traceId,
    },
  });
  // 从响应头更新 trace_id / Update trace_id from response
  const respTraceId = resp.headers.get("X-Trace-Id");
  if (respTraceId) {
    _currentTraceId = respTraceId;
  }
  return resp;
}

// ── 响应类型 / Response types ──

export interface TickEvent {
  type: string;
  tick: number;
  payload: Record<string, unknown>;
}

export interface EventsResponse {
  events: TickEvent[];
  display_tick: number;
  data_tick: number;
}

interface LoopStatus {
  running: boolean;
  batch_running: boolean;
}

/** GET /api/world/{id}/events?since_tick=... */
export async function fetchEvents(
  baseUrl: string,
  worldId: string,
  sinceTick: number
): Promise<EventsResponse> {
  const resp = await fetchWithTrace(
    `${baseUrl}/api/world/${worldId}/events?since_tick=${sinceTick}`
  );
  if (!resp.ok) throw new Error(`events ${resp.status}`);
  return (await resp.json()) as EventsResponse;
}

/** POST /api/world/{id}/tick/batch/{n} — 409 自动重试 / Auto-retry on 409 (batch still running) */
export async function triggerBatch(baseUrl: string, worldId: string, n: number): Promise<void> {
  for (let attempt = 0; attempt < 5; attempt++) {
    const resp = await fetchWithTrace(`${baseUrl}/api/world/${worldId}/tick/batch/${n}`, {
      method: "POST",
    });
    if (resp.ok) return;
    if (resp.status === 409 && attempt < 4) {
      await new Promise((r) => setTimeout(r, 1000));
      continue;
    }
    throw new Error(`batch/${n} ${resp.status}`);
  }
}

/** GET /api/world/{id}/loop/status */
export async function fetchLoopStatus(baseUrl: string, worldId: string): Promise<LoopStatus> {
  const resp = await fetchWithTrace(`${baseUrl}/api/world/${worldId}/loop/status`);
  if (!resp.ok) throw new Error(`loop/status ${resp.status}`);
  return (await resp.json()) as LoopStatus;
}

/** POST /api/world/{id}/loop/start */
export async function startLoop(baseUrl: string, worldId: string): Promise<void> {
  const resp = await fetchWithTrace(`${baseUrl}/api/world/${worldId}/loop/start`, {
    method: "POST",
  });
  if (!resp.ok) throw new Error(`loop/start ${resp.status}`);
}

/** POST /api/world/{id}/loop/pause */
export async function pauseLoop(baseUrl: string, worldId: string): Promise<void> {
  await fetchWithTrace(`${baseUrl}/api/world/${worldId}/loop/pause`, { method: "POST" });
}

/** POST /api/world/{id}/loop/resume */
export async function resumeLoop(baseUrl: string, worldId: string): Promise<void> {
  const resp = await fetchWithTrace(`${baseUrl}/api/world/${worldId}/loop/resume`, {
    method: "POST",
  });
  if (!resp.ok) throw new Error(`loop/resume ${resp.status}`);
}

/** POST /api/world/{id}/reset */
export async function resetWorld(baseUrl: string, worldId: string): Promise<void> {
  await fetchWithTrace(`${baseUrl}/api/world/${worldId}/reset`, { method: "POST" });
}

/** POST /api/world/{id}/tick/display/{tick} */
export async function syncDisplayTick(
  baseUrl: string,
  worldId: string,
  tick: number
): Promise<void> {
  await fetchWithTrace(`${baseUrl}/api/world/${worldId}/tick/display/${tick}`, { method: "POST" });
}

// ── 指标 API / Metrics API ──

export interface TickMetric {
  tick: number;
  world_id: string;
  latency_ms: number;
  llm_calls: number;
  tokens_in: number;
  tokens_out: number;
  events_count: number;
  estimated_cost_usd: number;
  action_types: Record<string, number>;
  errors: string[];
}

export interface MetricsSummary {
  total_ticks: number;
  total_tokens_in: number;
  total_tokens_out: number;
  total_cost_usd: number;
  avg_latency_ms: number;
  avg_tokens_per_tick: number;
}

/** GET /api/metrics/ticks */
export async function fetchTickMetrics(
  baseUrl: string,
  worldId: string,
  lastN = 20
): Promise<{ ticks: TickMetric[] }> {
  const resp = await fetchWithTrace(
    `${baseUrl}/api/metrics/ticks?world_id=${worldId}&last_n=${lastN}`
  );
  if (!resp.ok) return { ticks: [] };
  return (await resp.json()) as { ticks: TickMetric[] };
}

/** GET /api/metrics/summary */
export async function fetchMetricsSummary(
  baseUrl: string,
  worldId: string,
  lastN = 100
): Promise<MetricsSummary> {
  const resp = await fetchWithTrace(
    `${baseUrl}/api/metrics/summary?world_id=${worldId}&last_n=${lastN}`
  );
  if (!resp.ok) {
    return {
      total_ticks: 0,
      total_tokens_in: 0,
      total_tokens_out: 0,
      total_cost_usd: 0,
      avg_latency_ms: 0,
      avg_tokens_per_tick: 0,
    };
  }
  return (await resp.json()) as MetricsSummary;
}

/** GET /api/metrics/cost */
export async function fetchCostMetrics(
  baseUrl: string,
  worldId: string,
  lastN = 100
): Promise<Record<string, number>> {
  const resp = await fetchWithTrace(
    `${baseUrl}/api/metrics/cost?world_id=${worldId}&last_n=${lastN}`
  );
  if (!resp.ok) return {};
  return (await resp.json()) as Record<string, number>;
}
