/** 指标面板 / Metrics Panel — 显示 Tick 延迟、Token 消耗和成本 */
import { Panel } from "./Panel";
import { fetchMetricsSummary, type MetricsSummary } from "../client/api";

const WORLD_ID = "mock_world";

export class MetricsPanel extends Panel {
  private summaryEl!: HTMLDivElement;
  private refreshTimer: ReturnType<typeof setInterval> | null = null;

  constructor() {
    super("metrics-panel");
  }

  protected buildDOM(): HTMLElement {
    const container = document.createElement("div");
    container.style.cssText =
      "position:fixed;top:8px;right:8px;width:220px;padding:10px;" +
      "background:rgba(0,0,0,0.85);border:1px solid rgba(255,215,0,0.2);" +
      "border-radius:6px;color:#c8d6e5;font-size:12px;z-index:1000;";

    // 标题栏 / Title bar
    const title = document.createElement("div");
    title.style.cssText = "color:#ffd700;font-weight:bold;margin-bottom:6px;font-size:13px;";
    title.textContent = "\u{1F4CA} 监控面板";
    container.appendChild(title);

    // 指标内容 / Metrics content
    this.summaryEl = document.createElement("div");
    this.summaryEl.style.cssText = "line-height:1.8;";
    this.summaryEl.textContent = "等待数据...";
    container.appendChild(this.summaryEl);

    // 刷新按钮 / Refresh button
    const refreshBtn = document.createElement("button");
    refreshBtn.textContent = "\u{1F504}";
    refreshBtn.style.cssText =
      "position:absolute;top:8px;right:8px;background:none;border:none;" +
      "cursor:pointer;font-size:14px;color:#aaa;";
    refreshBtn.onclick = () => this.refresh();
    container.appendChild(refreshBtn);

    return container;
  }

  protected bindEvents(): void {
    // 自动刷新（每 10 秒）/ Auto-refresh every 10s
    this.refreshTimer = setInterval(() => this.refresh(), 10_000);
    // 首次刷新 / Initial refresh
    setTimeout(() => this.refresh(), 2000);
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

    this.summaryEl.innerHTML = [
      `\u23F1 平均延迟: <span style="color:#3498db">${s.avg_latency_ms.toFixed(0)}ms</span>`,
      `\u{1F524} Token入/出: <span style="color:#2ecc71">${s.total_tokens_in.toLocaleString()}</span> / <span style="color:#e67e22">${s.total_tokens_out.toLocaleString()}</span>`,
      `\u{1F4B0} 估算成本: <span style="color:#ffd700">${costStr}</span>`,
      `\u{1F4C8} 总 Tick: <span style="color:#9b59b6">${s.total_ticks}</span>`,
      `\u{1F4CA} 平均Token/Tick: <span style="color:#1abc9c">${s.avg_tokens_per_tick.toFixed(0)}</span>`,
    ].join("<br>");
  }

  /** 停止自动刷新 / Stop auto-refresh */
  stopAutoRefresh(): void {
    if (this.refreshTimer) {
      clearInterval(this.refreshTimer);
      this.refreshTimer = null;
    }
  }
}
