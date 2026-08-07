/** Vitest 全局 setup / Global test setup.
 *
 * jsdom 默认未实现 HTMLCanvasElement.getContext（项目刻意不安装原生 canvas 包），
 * 而 Phaser 在模块加载时会调用 CanvasFeatures 检测导致崩溃。这里在 setup 阶段
 * （早于测试文件 import）为 canvas 提供最小 2D context 桩，使依赖 Phaser 的模块
 * 能在 node 测试环境中被导入。
 */
function makeStubContext() {
  return {
    fillStyle: "",
    fillRect: () => {},
    getImageData: () => ({ data: new Uint8ClampedArray(4) }),
    createImageData: () => ({ data: new Uint8ClampedArray(4) }),
    putImageData: () => {},
  };
}

if (typeof HTMLCanvasElement !== "undefined") {
  try {
    // jsdom 可能把 getContext 定义成不可写的 accessor，先 delete 再重定义
    delete (HTMLCanvasElement.prototype as any).getContext;
  } catch {
    /* ignore */
  }
  try {
    Object.defineProperty(HTMLCanvasElement.prototype, "getContext", {
      configurable: true,
      writable: true,
      value: () => makeStubContext(),
    });
  } catch {
    /* ignore */
  }
}

if (typeof document !== "undefined" && typeof document.createElement === "function") {
  const origCreate = document.createElement.bind(document);
  document.createElement = function createElement(tag: string, ...rest: unknown[]) {
    const el = origCreate(tag, ...(rest as []));
    if ((tag || "").toLowerCase() === "canvas" && el) {
      try {
        delete (el as any).getContext;
      } catch {
        /* ignore */
      }
      try {
        Object.defineProperty(el, "getContext", {
          configurable: true,
          writable: true,
          value: () => makeStubContext(),
        });
      } catch {
        /* ignore */
      }
    }
    return el;
  } as typeof document.createElement;
}
