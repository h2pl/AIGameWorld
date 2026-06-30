/** 主游戏场景 / Main Game Scene — 瓦片地图 + 角色精灵 */

import Phaser from "phaser";
import { gameStore } from "../state/GameStore";
import { CharacterSprite } from "../objects/CharacterSprite";
import { CONFIG } from "../config";
import type { SceneData } from "../types";

export class GameScene extends Phaser.Scene {
  private tileGraphics!: Phaser.GameObjects.Graphics;
  private sprites: Map<string, CharacterSprite> = new Map();
  private tileSize: number = CONFIG.TILE.size;

  constructor() {
    super({ key: "GameScene" });
  }

  create(): void {
    this.tileGraphics = this.add.graphics();
    this.tileSize = CONFIG.TILE.size;

    // 监听状态变化 / Listen to state changes
    gameStore.subscribe((state) => {
      this.onStateUpdate(state);
    });

    // 如果有初始数据，绘制 / Draw if initial data loaded
    const state = gameStore.getState();
    if (state.scenes.length > 0) {
      this.drawTileMap(state.scenes[0], state.characters.length);
      this.updateSprites();
    }

    // 监听角色点击→通知外部 / Listen for character clicks
    this.events.on("character-clicked", (char: any) => {
      document.dispatchEvent(new CustomEvent("character-selected", { detail: char }));
    });

    // 初始提示 / Initial hint
    if (state.scenes.length === 0) {
      this.add.text(
        CONFIG.CANVAS.width / 2, CONFIG.CANVAS.height / 2 - 40,
        "AIGameWorld", {
          fontFamily: "Segoe UI, sans-serif",
          fontSize: "32px",
          color: CONFIG.COLOR.text,
        }).setOrigin(0.5);
      this.add.text(
        CONFIG.CANVAS.width / 2, CONFIG.CANVAS.height / 2 + 10,
        "aw -i 导入 pack 后刷新页面", {
          fontFamily: "Segoe UI, sans-serif",
          fontSize: "14px",
          color: CONFIG.COLOR.text_dim,
        }).setOrigin(0.5);
    }
  }

  private onStateUpdate(
    state: ReturnType<typeof gameStore.getState>,
  ): void {
    this.updateSprites();
  }

  /** 重绘所有角色 / Redraw all characters */
  private updateSprites(): void {
    const state = gameStore.getState();
    // 移除不存在的 / Remove sprites no longer present
    for (const [id, sprite] of this.sprites) {
      if (!state.characters.find((c: { id: string }) => c.id === id)) {
        sprite.destroy();
        this.sprites.delete(id);
      }
    }
    // 创建或更新 / Create or update
    for (const char of state.characters) {
      const pos = state.character_positions[char.id] || { x: char.position_x, y: char.position_y };
      const existing = this.sprites.get(char.id);
      if (existing) {
        existing.moveTo(pos.x, pos.y, 300);
        if (char.combat) {
          existing.updateHp(char.combat.hp, char.combat.max_hp);
        }
      } else {
        const sprite = new CharacterSprite(this, char, pos.x, pos.y, this.tileSize);
        this.sprites.set(char.id, sprite);
      }
    }
  }

  /** 绘制瓦片地图 / Draw tile map */
  drawTileMap(scene: SceneData, charCount: number): void {
    const g = this.tileGraphics;
    g.clear();
    const ts = this.tileSize;
    const maxCol = 30;
    const maxRow = 20;
    const centerCol = Math.floor(maxCol / 2);
    const centerRow = Math.floor(maxRow / 2);

    // 场景标题 / Scene title
    const sceneTypeLabel = scene.type === "village" ? "村庄" :
      scene.type === "indoor" ? "室内" : "户外";
    this.add.text(10, 10, `${scene.name} (${sceneTypeLabel})`, {
      fontFamily: "Segoe UI, sans-serif",
      fontSize: "14px",
      color: CONFIG.COLOR.text,
      fontStyle: "bold",
    }).setDepth(10);

    // 绘制格子 / Draw tiles
    for (let row = 0; row < maxRow; row++) {
      for (let col = 0; col < maxCol; col++) {
        const x = col * ts;
        const y = row * ts;
        let color = CONFIG.COLOR.tile_outdoor;

        if (scene.type === "indoor" || scene.type === "village") {
          color = CONFIG.COLOR.tile_floor;
          // 边框区域是墙 / Border tiles are walls
          if (row === 0 || row === maxRow - 1 || col === 0 || col === maxCol - 1) {
            color = CONFIG.COLOR.tile_wall;
          }
        }

        g.fillStyle(color, 0.8);
        g.fillRect(x + 1, y + 1, ts - 2, ts - 2);

        // 网格线 / Grid lines
        g.lineStyle(1, 0x000000, 0.15);
        g.strokeRect(x, y, ts, ts);
      }
    }

    // 地标 / Landmarks
    for (const lm of scene.landmarks) {
      const lx = (lm.position.x % maxCol) * ts + ts / 2;
      const ly = (lm.position.y % maxRow) * ts + ts / 2;
      g.fillStyle(0x8b6914, 0.5);
      g.fillRect(lx - ts / 2, ly - ts / 2, ts, ts);
      this.add.text(lx, ly + 14, lm.name, {
        fontFamily: "Segoe UI, sans-serif",
        fontSize: "9px",
        color: CONFIG.COLOR.text_dim,
      }).setOrigin(0.5).setDepth(10);
    }

    // 出口 / Exits
    for (const exit of scene.exits) {
      const ex = (exit.position.x % maxCol) * ts + ts / 2;
      const ey = (exit.position.y % maxRow) * ts + ts / 2;
      g.fillStyle(CONFIG.COLOR.tile_door, 0.6);
      g.fillRect(ex - ts / 3, ey - ts / 3, ts * 0.66, ts * 0.66);
      this.add.text(ex, ey + ts / 2 + 6, exit.description, {
        fontFamily: "Segoe UI, sans-serif",
        fontSize: "8px",
        color: CONFIG.COLOR.text_dim,
      }).setOrigin(0.5).setDepth(10);
    }

    // 场景描述文本 / Scene description
    const descLines = this.wrapText(scene.description, 30);
    const descY = maxRow * ts - 20;
    for (let i = 0; i < descLines.length && i < 3; i++) {
      this.add.text(10, descY - (descLines.length - i) * 14, descLines[i], {
        fontFamily: "Segoe UI, sans-serif",
        fontSize: "10px",
        color: CONFIG.COLOR.text_dim,
      }).setDepth(10);
    }

    // 统计 / Stats
    this.add.text(maxCol * ts - 10, 10, `角色: ${charCount}`, {
      fontFamily: "Segoe UI, sans-serif",
      fontSize: "12px",
      color: CONFIG.COLOR.text,
    }).setOrigin(1, 0).setDepth(10);
  }

  private wrapText(text: string, maxLen: number): string[] {
    const words = text.split(" ");
    const lines: string[] = [];
    let current = "";
    for (const w of words) {
      if ((current + " " + w).length > maxLen) {
        lines.push(current);
        current = w;
      } else {
        current = current ? current + " " + w : w;
      }
    }
    if (current) lines.push(current);
    return lines.length ? lines : [text];
  }
}
