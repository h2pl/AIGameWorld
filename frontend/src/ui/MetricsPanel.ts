/** 指标面板 / Metrics Panel — 显示 Tick 延迟、Token 消耗和成本
 *
 * 位置：右下角，不遮挡事件面板 / Positioned bottom-right to avoid event panel overlap
 * 可折叠：点击标题栏切换展开/收起 / Collapsible via title bar click
 */
import { Panel } from "./Panel";
import { fetchMetricsSummary, type MetricsSummary } from "../client/api";
import { worldStore } from "../state/WorldStore";

const WORLD_ID = "mock_world";

export class MetricsPanel extends Panel {
  private summaryEl!: HTMLDivElement;
  private refreshTimer: ReturnType<typeof setInterval> | null = null;
  private collapsed = false;
  private titleBar!: HTMLDivElement;
  private contentEl!: HTMLDivElement;

  constructor() {
    super("metrics-panel");
  }

  protected buildDOM(): HTMLElement {
    const container = document.createElement("div");
    container.style.cssText =
      "position:fixed;bottom:50px;right:10px;width:260px;" +
      "background:rgba(0,0,0,0.85);border:1px solid rgba(255,215,0,0.2);" +
      "border-radius:6px;color:#c8d6e5;font-size:12px;z-index:1000;" +
      "transition:all 0.2s ease;";

    // 标题栏（可点击折叠）/ Title bar (click to collapse)
    this.titleBar = document.createElement("div");
    this.titleBar.style.cssText =
      "color:#ffd700;font-weight:bold;padding:8px 10px;cursor:pointer;" +
      "display:flex;justify-content:space-between;align-items:center;" +
      "user-select:none;";
    this.titleBar.innerHTML =
      '<span>\u{1F4CA} 监控面板</span><span class="collapse-icon" style="font-size:10px;color:#aaa;">\u25BC</span>';
    this.titleBar.onclick = () => this._toggle();
    container.appendChild(this.titleBar);

    // 内容区 / Content area
    this.contentEl = document.createElement("div");
    this.contentEl.style.cssText =
      "padding:0 10px 10px;transition:max-height 0.3s ease;overflow:hidden;";

    this.summaryEl = document.createElement("div");
    this.summaryEl.style.cssText = "line-height:1.8;";
    this.summaryEl.textContent = "等待数据...";
    this.contentEl.appendChild(this.summaryEl);

    // 刷新按钮 / Refresh button
    const refreshBtn = document.createElement("button");
    refreshBtn.textContent = "\u{1F504}";
    refreshBtn.style.cssText =
      "background:none;border:none;cursor:pointer;font-size:12px;" +
      "color:#aaa;float:right;margin-top:4px;";
    refreshBtn.onclick = (e) => {
      e.stopPropagation();
      this.refresh();
    };
    this.contentEl.appendChild(refreshBtn);

    container.appendChild(this.contentEl);
    return container;
  }

  protected bindEvents(): void {
    // 自动刷新（每 10 秒）/ Auto-refresh every 10s
    this.refreshTimer = setInterval(() => this.refresh(), 10_000);
    // 首次刷新 / Initial refresh
    setTimeout(() => this.refresh(), 2000);
  }

  /** 折叠/展开 / Toggle collapse */
  private _toggle(): void {
    this.collapsed = !this.collapsed;
    const icon = this.titleBar.querySelector(".collapse-icon");
    if (this.collapsed) {
      this.contentEl.style.maxHeight = "0";
      this.contentEl.style.padding = "0 10px";
      if (icon) icon.textContent = "\u25B6";
    } else {
      this.contentEl.style.maxHeight = "400px";
      this.contentEl.style.padding = "0 10px 10px";
      if (icon) icon.textContent = "\u25BC";
    }
  }

  /** 刷新指标 / Refresh metrics */
  async refresh(): Promise<void> {
    try {
      const baseUrl = "";
      const summary = await fetchMetricsSummary(baseUrl, WORLD_ID, 100);
      this._render(summary);
    } catch {
      this.summaryEl.textContent = "获取失败";
    }
  }

  private _render(s: MetricsSummary): void {
    if (s.total_ticks === 0) {
      this.summaryEl.textContent = "暂无数据";
      return;
    }

    const costStr = s.total_cost_usd < 0.01 ? `<$0.01` : `$${s.total_cost_usd.toFixed(4)}`;
    // 当前 display_tick（与游戏画面一致）/ Current display_tick from worldStore
    const displayTick = worldStore.getState().display_tick;

    // 分阶段延迟 / Per-stage latency breakdown
    const stages = s.avg_stage_latencies || {};
    const stageLines = Object.entries(stages)
      .sort((a, b) => b[1] - a[1])
      .map(([name, ms]) => {
        const sec = (ms / 1000).toFixed(1);
        return `&nbsp;&nbsp;<span style="color:#7f8c8d">${name}</span> <span style="color:#3498db">${sec}s</span>`;
      });

    const lines: string[] = [];
    // 当前 Tick 行：display_tick（画面）+ 总处理数 / Current tick line
    if (displayTick > 0) {
      lines.push(
        `\u{1F4C8} 当前: <span style="color:#9b59b6">Tick ${displayTick}</span> | 已处理: <span style="color:#9b59b6">${s.total_ticks}</span>`
      );
    } else {
      lines.push(`\u{1F4C8} 已处理: <span style="color:#9b59b6">${s.total_ticks}</span> ticks`);
    }
    // 分阶段延迟 / Per-stage latencies
    lines.push(
      `\u23F1 平均延迟: <span style="color:#3498db">${(s.avg_latency_ms / 1000).toFixed(1)}s</span>`
    );
    if (stageLines.length) {
      lines.push(...stageLines);
    }
    // Token + 成本 / Tokens + cost
    lines.push(
      `\u{1F524} Token: <span style="color:#2ecc71">${s.total_tokens_in.toLocaleString()}</span>/<span style="color:#e67e22">${s.total_tokens_out.toLocaleString()}</span>`,
      `\u{1F4B0} 成本: <span style="color:#ffd700">${costStr}</span> | <span style="color:#1abc9c">${s.avg_tokens_per_tick.toFixed(0)}</span>/tick`
    );

    this.summaryEl.innerHTML = lines.join("<br>");
  }

  /** 停止自动刷新 / Stop auto-refresh */
  stopAutoRefresh(): void {
    if (this.refreshTimer) {
      clearInterval(this.refreshTimer);
      this.refreshTimer = null;
    }
  }
}
