// -- file start -- / file start
/** 播放状态 / Play state — 供动画/对话逐步检查 abort */
let _playing = true;

export const playState = {
  get playing(): boolean { return _playing; },
  set playing(v: boolean) { _playing = v; },
};
