// -- file start -- / file start
/** 控制栏 / Control Bar — 按钮 + 状态显示，通过回调暴露行为 */
import { Panel } from "./Panel";
import { setSpeed, speedOptions } from "../config/playback";

type RunState = "idle" | "connecting" | "running" | "paused";

export interface ControlBarCallbacks {
  onRun: (n: number) => Promise<void>;
  onStart: () => Promise<void>;
  onPause: () => Promise<void>;
  onResume: () => Promise<void>;
  onReset: () => Promise<void>;
  getTickCount: () => number;
}

export class ControlBar extends Panel {
  private runState: RunState = "idle";
  private statusEl!: HTMLSpanElement;
  private tInput!: HTMLInputElement;
  private btnRunN!: HTMLButtonElement;
  private btnStart!: HTMLButtonElement;
  private btnPause!: HTMLButtonElement;
  private btnResume!: HTMLButtonElement;
  private btnReset!: HTMLButtonElement;
  private callbacks: ControlBarCallbacks | null = null;

  constructor() {
    super("control-bar");
  }

  /** 设置回调 / Set callbacks after construction */
  setCallbacks(cbs: ControlBarCallbacks): void {
    this.callbacks = cbs;
  }

  /** 更新状态文本 / Update status text */
  setStatus(text: string): void {
    this.statusEl.textContent = text;
    this.statusEl.classList.remove("control-status-waiting");
  }

  /** 设置等待状态 / Set waiting-for-tick state */
  setWaiting(isWaiting: boolean, text = "等待后端生成 Tick 数据..."): void {
    if (isWaiting) {
      this.statusEl.textContent = text;
      this.statusEl.classList.add("control-status-waiting");
    } else {
      this.statusEl.classList.remove("control-status-waiting");
    }
  }

  /** 初始化按钮为就绪状态 / Initialize buttons ready */
  initReady(backendReady: boolean): void {
    this.statusEl.textContent = backendReady ? "就绪" : "后端未就绪";
    this._updateButtons();
  }

  protected buildDOM(): HTMLElement {
    const bar = document.createElement("div");
    bar.style.cssText =
      "position:fixed;bottom:8px;left:50%;transform:translateX(-50%);display:flex;gap:8px;z-index:999;align-items:center;";

    this.tInput = document.createElement("input");
    this.tInput.value = "3";
    this.tInput.style.cssText =
      "width:50px;text-align:center;border-radius:4px;border:1px solid #555;background:#222;color:#fff;";
    bar.appendChild(this.tInput);

    this.btnRunN = this._btn("跑N个Tick", "#8e44ad");
    bar.appendChild(this.btnRunN);
    bar.appendChild(this._sep());
    this.btnStart = this._btn("▶ 开始", "#2ecc71");
    this.btnPause = this._btn("⏸ 暂停", "#f39c12");
    this.btnResume = this._btn("⏯ 恢复", "#3498db");
    this.btnReset = this._btn("⏹ 重置", "#e74c3c");
    bar.appendChild(this.btnStart);
    bar.appendChild(this.btnPause);
    bar.appendChild(this.btnResume);
    bar.appendChild(this.btnReset);
    bar.appendChild(this._sep());

    // 倍速按钮 / Speed buttons
    bar.appendChild(this._sep());
    const speedBtns: HTMLButtonElement[] = [];
    for (const s of speedOptions()) {
      const btn = this._btn(`${s}x`, s === 1 ? "#555" : "#e67e22");
      btn.style.padding = "4px 8px";
      btn.onclick = () => {
        setSpeed(s);
        speedBtns.forEach(
          (b, i) => (b.style.background = speedOptions()[i] === s ? "#e67e22" : "#555")
        );
      };
      bar.appendChild(btn);
      speedBtns.push(btn);
    }

    this.statusEl = document.createElement("span");
    this.statusEl.style.cssText =
      "padding:6px 14px;border-radius:4px;background:rgba(0,0,0,0.7);color:#ffd700;font-size:13px;font-weight:bold;min-width:180px;text-align:center;border:1px solid rgba(255,215,0,0.3);";
    bar.appendChild(this.statusEl);

    // 按钮行为绑定（方法在 bindEvents 中设置，确保 callbacks 已注入）
    return bar;
  }

  protected bindEvents(): void {
    this.btnRunN.onclick = () => this._handleRun();
    this.btnStart.onclick = () => this._handleStart();
    this.btnPause.onclick = () => this._handlePause();
    this.btnResume.onclick = () => this._handleResume();
    this.btnReset.onclick = () => this._handleReset();

    window.addEventListener("tick-waiting", ((ev: CustomEvent) => {
      const { waiting, message } = (ev.detail || {}) as { waiting?: boolean; message?: string };
      this.setWaiting(!!waiting, message);
    }) as EventListener);
  }

  /** 跑 N 个 tick / Run N ticks */
  private async _handleRun(): Promise<void> {
    if (this.runState !== "idle" || !this.callbacks) return;
    const n = parseInt(this.tInput.value) || 1;
    this.runState = "connecting";
    this._updateButtons();
    try {
      this.runState = "running";
      this._updateButtons();
      this.statusEl.textContent = "运行中...";
      await this.callbacks.onRun(n);
      this.statusEl.textContent = `完成: ${this.callbacks.getTickCount()} tick`;
    } catch {
      this.statusEl.textContent = "错误";
    } finally {
      this.runState = "idle";
      this._updateButtons();
    }
  }

  // 开始循环 / Start loop
  private async _handleStart(): Promise<void> {
    if (this.runState !== "idle" || !this.callbacks) return;
    this.runState = "connecting";
    this._updateButtons();
    try {
      this.runState = "running";
      this._updateButtons();
      this.statusEl.textContent = "持续运行中...";
      await this.callbacks.onStart();
    } catch {
      this.runState = "idle";
      this._updateButtons();
      this.statusEl.textContent = "错误";
    }
  }

  // 暂停 / Pause
  private async _handlePause(): Promise<void> {
    if (this.runState !== "running" || !this.callbacks) return;
    try {
      await this.callbacks.onPause();
      this.runState = "paused";
      this._updateButtons();
      this.statusEl.textContent = "已暂停";
    } catch {
      /* ignore */
    }
  }

  // 恢复 / Resume
  private async _handleResume(): Promise<void> {
    if (this.runState !== "paused" || !this.callbacks) return;
    this.runState = "connecting";
    this._updateButtons();
    try {
      this.runState = "running";
      this._updateButtons();
      this.statusEl.textContent = "持续运行中...";
      await this.callbacks.onResume();
    } catch {
      this.runState = "paused";
      this._updateButtons();
      this.statusEl.textContent = "错误";
    }
  }

  // 重置 / Reset
  private async _handleReset(): Promise<void> {
    if (this.runState === "running" || !this.callbacks) return;
    try {
      await this.callbacks.onReset();
      this.statusEl.textContent = "已重置";
    } catch {
      this.statusEl.textContent = "重置失败";
    } finally {
      this.runState = "idle";
      this._updateButtons();
    }
  }

  private _updateButtons(): void {
    const idle = this.runState === "idle";
    const running = this.runState === "running";
    const paused = this.runState === "paused";
    const en = idle;
    this.btnRunN.disabled = !en;
    this.btnRunN.style.opacity = en ? "1" : "0.4";
    this.btnStart.disabled = !en;
    this.btnStart.style.display = idle || running ? "inline-block" : "none";
    this.btnStart.style.opacity = en ? "1" : "0.4";
    this.btnPause.disabled = !running;
    this.btnPause.style.display = idle || running ? "inline-block" : "none";
    this.btnPause.style.opacity = running ? "1" : "0.4";
    this.btnResume.style.display = paused ? "inline-block" : "none";
    this.btnReset.disabled = running;
    this.btnReset.style.opacity = running ? "0.4" : "1";
  }

  private _btn(text: string, bg: string): HTMLButtonElement {
    const b = document.createElement("button");
    b.textContent = text;
    b.style.cssText = `padding:4px 12px;border-radius:4px;border:none;background:${bg};color:#fff;cursor:pointer;`;
    return b;
  }

  private _sep(): HTMLDivElement {
    const d = document.createElement("div");
    d.style.width = "24px";
    return d;
  }
}
