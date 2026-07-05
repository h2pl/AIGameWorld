// -- file start -- / file start
/** 纹理生成工具 / Texture generation utilities — Canvas 程序化纹理 */
import Phaser from "phaser";

const RACE_SKIN: Record<string, string> = {
  human: "#f5cba7", elf: "#fdebd0", dwarf: "#d4a574",
  halfling: "#f5c6a0", orc: "#6b8e5a", tiefling: "#c48b9d", dragonborn: "#8b5e3c",
};
const RACE_HAIR: Record<string, string> = {
  human: "#4a2c0a", elf: "#d4c0a0", dwarf: "#8b4513",
  halfling: "#6b3a1f", orc: "#1a1a1a", tiefling: "#2c0033", dragonborn: "#3c1a00",
};
const ROLE_COLOR: Record<string, string> = {
  fighter: "#c0392b", rogue: "#2c3e50", cleric: "#f0f0f0", wizard: "#5b2c6f",
  ranger: "#27ae60", paladin: "#f1c40f", blacksmith: "#a0522d", guard: "#2980b9",
  merchant: "#16a085", innkeeper: "#d35400", boss: "#e74c3c", enemy: "#c0392b",
  villager: "#95a5a6",
};

/** 生成角色 Canvas 纹理 / Generate character Canvas texture */
export function makeCharTexture(
  scene: Phaser.Scene,
  ch: { id: string; race: string | null; role: string; is_pc: boolean; functions?: string[] },
  size: number
): void {
  if (scene.textures.exists(ch.id)) return;
  const skin = RACE_SKIN[ch.race || ""] || "#f5cba7";
  const hair = RACE_HAIR[ch.race || ""] || "#4a2c0a";
  const body = ROLE_COLOR[ch.role] ||
    (ch.functions?.[0] ? ROLE_COLOR[ch.functions[0]] || "#7f8c8d" : "#7f8c8d");
  const cv = scene.textures.createCanvas(ch.id, size, size);
  if (!cv) return;
  const c = cv.context;
  c.imageSmoothingEnabled = false;
  const cx = size / 2;
  c.fillStyle = body;  c.fillRect(cx - 6, 11, 12, 10);
  c.fillStyle = skin;  c.beginPath(); c.arc(cx, 9, 6, 0, Math.PI * 2); c.fill();
  c.fillStyle = hair;  c.beginPath(); c.arc(cx, 7, 6, Math.PI, Math.PI * 2); c.fill();
  c.fillStyle = "#fff"; c.fillRect(cx - 2, 8, 1, 2); c.fillRect(cx + 1, 8, 1, 2);
  c.fillStyle = "#000"; c.fillRect(cx - 2, 9, 1, 1); c.fillRect(cx + 1, 9, 1, 1);
  c.fillStyle = "#2c3e50"; c.fillRect(cx - 4, 20, 4, 6); c.fillRect(cx + 1, 20, 4, 6);
  if (ch.is_pc) { c.fillStyle = "#ffd700"; c.fillRect(cx - 7, 12, 3, 3); c.fillRect(cx + 4, 12, 3, 3); }
  cv.refresh();
}

/** 生成场景物品纹理 / Generate scene object texture */
export function makeObjectTexture(
  scene: Phaser.Scene,
  obj: { id: string; object_type: string },
  key: string,
  size: number
): void {
  const colors: Record<string, string> = { container: "#d4a017", door: "#8b6914", landmark: "#ccc" };
  const fill = colors[obj.object_type] || "#888";
  const cv = scene.textures.createCanvas(key, size, size);
  if (!cv) return;
  const c = cv.context; c.imageSmoothingEnabled = false; c.fillStyle = fill;
  if (obj.object_type === "container") { c.fillRect(4, 10, 24, 16); c.fillStyle = "#fff"; c.fillRect(12, 16, 8, 2); }
  else if (obj.object_type === "door") { c.fillRect(8, 4, 16, 24); }
  else { c.beginPath(); c.arc(size / 2, size / 2, 8, 0, Math.PI * 2); c.fill(); }
  cv.refresh();
}
