// -- file start -- / file start
/** 播放倍速 / Playback speed multiplier */
const SPEEDS = [1, 1.5, 2, 4] as const;

let _speed: number = 1;

/** 当前倍速 / Current speed */
export function getSpeed(): number {
  return _speed;
}

/** 设置倍速 / Set speed (clamped to available options) */
export function setSpeed(s: number): number {
  const valid = SPEEDS.includes(s as any) ? s : SPEEDS[SPEEDS.length - 1];
  _speed = valid;
  return _speed;
}

/** 可用倍速列表 / Available speeds */
export function speedOptions(): readonly number[] {
  return SPEEDS;
}

/** 应用倍速到毫秒数 / Apply speed to ms (smaller = faster) */
export function speedMs(ms: number): number {
  return Math.round(ms / _speed);
}
