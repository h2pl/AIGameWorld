// --- 测试 / Tests ---
/** 倍速播放单元测试 / Playback speed unit tests */
import { describe, it, expect, beforeEach } from "vitest";
import { getSpeed, setSpeed, speedMs, speedOptions } from "../../../src/config/playback";

describe("playback config", () => {
  beforeEach(() => { setSpeed(1); });

  it("should default to 1x speed", () => {
    expect(getSpeed()).toBe(1);
  });

  it("should provide 4 speed options", () => {
    expect(speedOptions()).toEqual([1, 1.5, 2, 4]);
  });

  it("should scale time by speed factor", () => {
    expect(speedMs(200)).toBe(200);
    setSpeed(2);
    expect(speedMs(200)).toBe(100);
    setSpeed(4);
    expect(speedMs(200)).toBe(50);
  });

  it("should round fractional ms values", () => {
    setSpeed(1.5);
    expect(speedMs(500)).toBe(333);
  });

  it("should handle 4x correctly", () => {
    setSpeed(4);
    expect(speedMs(800)).toBe(200);
    expect(speedMs(40)).toBe(10);
  });

  it("should reject invalid speeds gracefully", () => {
    setSpeed(99);
    expect(getSpeed()).toBe(4);
    setSpeed(-1);
    expect(getSpeed()).toBe(4);
  });
});
