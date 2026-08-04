/** 背景音乐播放器 — Web Audio API 生成环境音 / BGM player using Web Audio API */
export class BGMPlayer {
  private ctx: AudioContext | null = null;
  private gainNode: GainNode | null = null;
  private playing = false;
  private nodes: AudioNode[] = [];

  /** 初始化（需用户交互后调用）/ Init (must be called after user interaction) */
  async play(): Promise<void> {
    if (this.playing) return;
    this.ctx = new AudioContext();
    this.gainNode = this.ctx.createGain();
    this.gainNode.gain.value = 0.12;
    this.gainNode.connect(this.ctx.destination);

    this._startDrone();
    this._startPads();
    this.playing = true;
  }

  /** 停止 / Stop */
  stop(): void {
    this.playing = false;
    for (const n of this.nodes) {
      try {
        (n as AudioScheduledSourceNode).stop();
      } catch {
        /* already stopped */
      }
    }
    this.nodes = [];
    this.ctx?.close();
    this.ctx = null;
  }

  /** 暂停/恢复 / Toggle */
  setPaused(v: boolean): void {
    if (this.gainNode) {
      this.gainNode.gain.linearRampToValueAtTime(v ? 0 : 0.12, (this.ctx?.currentTime ?? 0) + 0.3);
    }
  }

  /** 持续低音底噪 / Deep drone */
  private _startDrone(): void {
    const ctx = this.ctx!;
    const freqs = [65.4, 98, 130.8]; // C2, G2, C3
    for (const freq of freqs) {
      const osc = ctx.createOscillator();
      osc.type = "sine";
      osc.frequency.value = freq + Math.random() * 2 - 1;
      const g = ctx.createGain();
      g.gain.value = 0.3;
      osc.connect(g).connect(this.gainNode!);
      osc.start();
      this.nodes.push(osc);
      // 微微波动 / Slight wobble
      this._wobble(g, 0.2, 0.35, 4 + Math.random() * 3);
    }
  }

  /** 空灵音色层 / Ethereal pad layer */
  private _startPads(): void {
    const ctx = this.ctx!;
    const notes = [
      { freq: 262, delay: 0 },
      { freq: 330, delay: 8 },
      { freq: 392, delay: 16 },
      { freq: 330, delay: 24 },
    ]; // C4-E4-G4-E4 arpeggio
    for (const { freq, delay } of notes) {
      const osc = ctx.createOscillator();
      osc.type = "triangle";
      osc.frequency.value = freq;
      const g = ctx.createGain();
      g.gain.value = 0;
      const filter = ctx.createBiquadFilter();
      filter.type = "lowpass";
      filter.frequency.value = 800;
      osc.connect(filter).connect(g).connect(this.gainNode!);
      osc.start(ctx.currentTime + delay);
      this.nodes.push(osc);
      // 渐入渐出 / Fade in-out
      this._padFade(g, delay, 10, 22);
    }
  }

  private _wobble(g: GainNode, min: number, max: number, dur: number): void {
    const update = () => {
      if (!this.playing) return;
      const t = this.ctx!.currentTime;
      g.gain.linearRampToValueAtTime(min + Math.random() * (max - min), t + dur);
      setTimeout(update, dur * 1000);
    };
    update();
  }

  private _padFade(g: GainNode, delay: number, fadeIn: number, fadeOut: number): void {
    const ctx = this.ctx!;
    const t = ctx.currentTime + delay;
    g.gain.setValueAtTime(0, t);
    g.gain.linearRampToValueAtTime(0.25, t + fadeIn);
    g.gain.linearRampToValueAtTime(0, t + fadeOut);
  }
}
