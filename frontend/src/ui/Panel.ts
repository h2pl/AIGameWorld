/** 面板基类 / Panel Base — mount → bindStore → show/hide → destroy */
export abstract class Panel {
  protected el!: HTMLElement;
  protected containerId: string;

  constructor(containerId: string) {
    this.containerId = containerId;
  }

  mount(parent: HTMLElement): void {
    this.el = this.buildDOM();
    this.el.id = this.containerId;
    parent.appendChild(this.el);
    this.bindStore?.();
    this.bindEvents?.();
  }

  protected abstract buildDOM(): HTMLElement;

  /** 子类可选：绑定事件 / Bind window events */
  protected bindStore?(): void;

  /** 子类可选：绑定 DOM 事件 / Bind DOM events */
  protected bindEvents?(): void;

  show(): void {
    this.el.style.display = "block";
  }
  hide(): void {
    this.el.style.display = "none";
  }
  destroy(): void {
    this.el?.remove();
  }
}
