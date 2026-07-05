/** HTTP API 层 / HTTP API layer — 纯网络调用，无业务逻辑 */
import type { EventData } from "../types";

const L = "[API]";

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
  const resp = await fetch(`${baseUrl}/api/world/${worldId}/events?since_tick=${sinceTick}`);
  if (!resp.ok) throw new Error(`events ${resp.status}`);
  return (await resp.json()) as EventsResponse;
}

/** POST /api/world/{id}/tick/batch/{n} */
export async function triggerBatch(baseUrl: string, worldId: string, n: number): Promise<void> {
  const resp = await fetch(`${baseUrl}/api/world/${worldId}/tick/batch/${n}`, { method: "POST" });
  if (!resp.ok) throw new Error(`batch/${n} ${resp.status}`);
}

/** GET /api/world/{id}/loop/status */
export async function fetchLoopStatus(baseUrl: string, worldId: string): Promise<LoopStatus> {
  const resp = await fetch(`${baseUrl}/api/world/${worldId}/loop/status`);
  if (!resp.ok) throw new Error(`loop/status ${resp.status}`);
  return (await resp.json()) as LoopStatus;
}

/** POST /api/world/{id}/loop/start */
export async function startLoop(baseUrl: string, worldId: string): Promise<void> {
  const resp = await fetch(`${baseUrl}/api/world/${worldId}/loop/start`, { method: "POST" });
  if (!resp.ok) throw new Error(`loop/start ${resp.status}`);
}

/** POST /api/world/{id}/loop/pause */
export async function pauseLoop(baseUrl: string, worldId: string): Promise<void> {
  await fetch(`${baseUrl}/api/world/${worldId}/loop/pause`, { method: "POST" });
}

/** POST /api/world/{id}/loop/resume */
export async function resumeLoop(baseUrl: string, worldId: string): Promise<void> {
  const resp = await fetch(`${baseUrl}/api/world/${worldId}/loop/resume`, { method: "POST" });
  if (!resp.ok) throw new Error(`loop/resume ${resp.status}`);
}

/** POST /api/world/{id}/reset */
export async function resetWorld(baseUrl: string, worldId: string): Promise<void> {
  await fetch(`${baseUrl}/api/world/${worldId}/reset`, { method: "POST" });
}

/** POST /api/world/{id}/tick/display/{tick} */
export async function syncDisplayTick(
  baseUrl: string,
  worldId: string,
  tick: number
): Promise<void> {
  await fetch(`${baseUrl}/api/world/${worldId}/tick/display/${tick}`, { method: "POST" });
}
