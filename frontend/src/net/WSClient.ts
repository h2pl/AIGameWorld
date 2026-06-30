/** WebSocket 客户端 / WebSocket Client — 连接后端驱动 tick 实时更新 */
import { gameStore } from "../state/GameStore";
import { CONFIG } from "../config";

type WSMessage = {
  type: "init_ok" | "tick" | "done" | "pong" | "error";
  data: Record<string, unknown>;
};

export class WSClient {
  private ws: WebSocket | null = null;
  private url: string;
  private reconnectTimer: ReturnType<typeof setTimeout> | null = null;

  constructor(sessionId: string) {
    this.url = `${CONFIG.API.ws}/${sessionId}`;
    console.log("[WS] created, url=", this.url);
  }

  /** 连接并初始化 / Connect and init */
  connect(packId: string): Promise<void> {
    return new Promise((resolve, reject) => {
      console.log("[WS] connecting to", this.url);
      this.ws = new WebSocket(this.url);

      this.ws.onopen = () => {
        console.log("[WS] connected, sending init pack_id=", packId);
        this.ws!.send(JSON.stringify({ cmd: "init", pack_id: packId }));
      };

      this.ws.onmessage = (ev) => {
        try {
          const msg: WSMessage = JSON.parse(ev.data);
          console.log("[WS] recv:", msg.type, msg.type === "tick" ? `tick=${(msg.data as Record<string, unknown>).tick}` : "");

          if (msg.type === "init_ok") {
            const d = msg.data as Record<string, unknown>;
            const chars = d.characters as unknown[];
            console.log("[WS] init_ok: chars=%d pack=%s", chars?.length || 0, d.pack_id);
            // 写入 gameStore / Update gameStore
            gameStore.setWorldState(
              d.pack_id as string,
              gameStore.getState().scenes, // 保持现有场景
              chars as never,
              [],
              [],
            );
            resolve();
          } else if (msg.type === "tick") {
            const d = msg.data as Record<string, unknown>;
            const moves = d.character_moves as Array<{ character_id: string; x: number; y: number }> | undefined;
            console.log("[WS] tick %d: narrative=%s moves=%d",
              d.tick, (d.narrative as string || "").slice(0, 40), moves?.length || 0);

            // 更新角色位置 / Update character positions
            if (moves) {
              const pos: Record<string, { x: number; y: number }> = {};
              for (const m of moves) pos[m.character_id] = { x: m.x, y: m.y };
              gameStore.updatePositions(pos);
            }
            gameStore.applyTickUpdate({ type: "tick_complete", data: d as never });
          } else if (msg.type === "done") {
            console.log("[WS] done: final tick=%d", (msg.data as Record<string, unknown>).tick);
          } else if (msg.type === "error") {
            console.error("[WS] error:", msg.data);
            reject(new Error(String(msg.data)));
          }
        } catch (e) {
          console.error("[WS] parse error:", e);
        }
      };

      this.ws.onerror = (e) => {
        console.error("[WS] connection error", e);
        reject(new Error("WS connect failed"));
      };

      this.ws.onclose = (e) => {
        console.log("[WS] closed: code=%d reason=%s", e.code, e.reason);
        this.scheduleReconnect(packId);
      };
    });
  }

  /** 运行 N 个 tick / Run N ticks */
  runTicks(n: number): void {
    if (!this.ws || this.ws.readyState !== WebSocket.OPEN) {
      console.error("[WS] runTicks: not connected");
      return;
    }
    console.log("[WS] sending run cmd: ticks=%d", n);
    this.ws.send(JSON.stringify({ cmd: "run", ticks: n }));
  }

  /** 关闭 / Close */
  close(): void {
    console.log("[WS] closing");
    if (this.reconnectTimer) clearTimeout(this.reconnectTimer);
    this.ws?.close();
  }

  private scheduleReconnect(packId: string): void {
    console.log("[WS] scheduling reconnect in 3s");
    this.reconnectTimer = setTimeout(() => {
      console.log("[WS] reconnecting...");
      this.connect(packId).catch(() => {});
    }, 3000);
  }
}
