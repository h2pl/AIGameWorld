/** WebSocket 客户端 / WebSocket Client — 连接后端驱动 tick 实时更新 */

import { gameStore } from "../state/GameStore";
import { CONFIG } from "../config";
import type { TickUpdate } from "../types";

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
  }

  /** 连接并初始化 / Connect and init */
  connect(packId: string): Promise<void> {
    return new Promise((resolve, reject) => {
      this.ws = new WebSocket(this.url);
      this.ws.onopen = () => {
        this.ws!.send(JSON.stringify({ cmd: "init", pack_id: packId }));
      };
      this.ws.onmessage = (ev) => {
        const msg: WSMessage = JSON.parse(ev.data);
        if (msg.type === "init_ok") {
          const d = msg.data as Record<string, unknown>;
          console.log("[WS] init ok, chars:", (d.characters as unknown[])?.length);
          resolve();
        }
      };
      this.ws.onerror = () => reject(new Error("WS connect failed"));
      this.ws.onclose = () => this.scheduleReconnect(packId);
    });
  }

  /** 运行 N 个 tick / Run N ticks */
  runTicks(n: number): void {
    if (!this.ws || this.ws.readyState !== WebSocket.OPEN) return;
    this.ws.send(JSON.stringify({ cmd: "run", ticks: n }));
    this.ws.onmessage = (ev) => {
      const msg: WSMessage = JSON.parse(ev.data);
      switch (msg.type) {
        case "tick":
          gameStore.applyTickUpdate({
            type: "tick_complete",
            data: msg.data as never,
          });
          break;
        case "done":
          console.log("[WS] done, tick:", (msg.data as Record<string, unknown>).tick);
          break;
      }
    };
  }

  /** 关闭 / Close */
  close(): void {
    if (this.reconnectTimer) clearTimeout(this.reconnectTimer);
    this.ws?.close();
  }

  private scheduleReconnect(packId: string): void {
    this.reconnectTimer = setTimeout(() => {
      console.log("[WS] reconnecting...");
      this.connect(packId).catch(() => {});
    }, 3000);
  }
}
