/** 世界坐标 → 屏幕(CSS 像素) 投影 / World → Screen (CSS pixel) projection
 *
 * 用于纯 DOM 文本（角色名/对话泡泡）跟随相机。
 * 关键要点：
 * - worldToScreen 返回「相对 canvas 显示区域左上角」的坐标（因为 camera.worldView
 *   基于游戏内部分辨率，canvas.getBoundingClientRect 反映 FIT 后实际显示尺寸）。
 * - DOM 文本必须挂在与 canvas 显示区域原点对齐的覆盖层（overlay）上，否则 FIT 居中
 *   （CENTER_BOTH letterbox）会让 #app 与 canvas 原点不一致，导致恒定偏移。
 * - 投影同时考虑相机 zoom（worldView 已含 zoom 后的可见范围）与 FIT 缩放。
 */
import Phaser from "phaser";

export interface ScreenPoint {
  x: number;
  y: number;
}

let overlayEl: HTMLElement | null = null;

/** 返回与 canvas 显示区域对齐的 DOM 覆盖层（懒创建，全局复用）/
 *  Return a DOM overlay aligned to the canvas display rect (lazy, shared). */
export function getOverlayHost(scene: Phaser.Scene): HTMLElement {
  const canvas = scene.game.canvas;
  const parent = (canvas?.parentElement as HTMLElement) ?? document.body;
  if (!overlayEl) {
    overlayEl = document.createElement("div");
    overlayEl.id = "agw-dom-overlay";
    overlayEl.style.position = "absolute";
    overlayEl.style.pointerEvents = "none"; // 默认穿透，泡泡单独开启
    overlayEl.style.overflow = "hidden"; // 裁切视野外的文本
    overlayEl.style.zIndex = "400";
    parent.appendChild(overlayEl);
  }
  // 每帧把覆盖层对齐到 canvas 显示区域（相对 parent）/ Align overlay to canvas each call
  const cr = canvas.getBoundingClientRect();
  const pr = parent.getBoundingClientRect();
  overlayEl.style.left = `${cr.left - pr.left}px`;
  overlayEl.style.top = `${cr.top - pr.top}px`;
  overlayEl.style.width = `${cr.width}px`;
  overlayEl.style.height = `${cr.height}px`;
  return overlayEl;
}

/** 世界坐标 → 相对 canvas 显示区域左上角的 CSS 坐标 / World → CSS coord relative to canvas */
export function worldToScreen(scene: Phaser.Scene, wx: number, wy: number): ScreenPoint {
  const cam = scene.cameras.main;
  const canvas = scene.game.canvas;
  const rect = canvas.getBoundingClientRect();
  const vx = cam.worldView.x;
  const vy = cam.worldView.y;
  const vw = cam.worldView.width;
  const vh = cam.worldView.height;
  return {
    x: ((wx - vx) / vw) * rect.width,
    y: ((wy - vy) / vh) * rect.height,
  };
}
