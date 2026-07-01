/** 面板基类 / Panel Base — 统一生命周期：mount → bindStore → show/hide → destroy */
import type { GameState } from "../state/GameStore";

export abstract class Panel {
  protected el!: HTMLElement;
  protected unsubscribe: (() => void) | null = null;
  protected containerId: string;

  constructor(containerId: string) {
    this.containerId = containerId;
  }

  /** 创建 DOM 并挂载到父容器 / Create DOM and mount */
  mount(parent: HTMLElement): void {
    this.el = this.buildDOM();
    this.el.id = this.containerId;
    parent.appendChild(this.el);
    this.bindStore?.();
    this.bindEvents?.();
  }

  /** 子类实现：构建面板 HTML / Build panel HTML */
  protected abstract buildDOM(): HTMLElement;

  /** 子类可选：绑定 GameStore / Bind store */
  protected bindStore?(): void;

  /** 子类可选：绑定 DOM 事件 / Bind DOM events */
  protected bindEvents?(): void;

  /** 显示面板 / Show panel */
  show(): void {
    this.el.style.display = "block";
  }

  /** 隐藏面板 / Hide panel */
  hide(): void {
    this.el.style.display = "none";
  }

  /** 销毁 / Destroy */
  destroy(): void {
    this.unsubscribe?.();
    this.el?.remove();
  }
}
