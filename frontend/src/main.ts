/** AIGameWorld 前端入口 / Frontend entry point. */
import Phaser from "phaser";

// Phaser 3 游戏配置 / Phaser 3 game config
const config: Phaser.Types.Core.GameConfig = {
  type: Phaser.AUTO,          // 自动选择 WebGL/Canvas / Auto-select renderer
  width: 960,                 // 画布宽度 / Canvas width
  height: 640,                // 画布高度 / Canvas height
  parent: "game",             // DOM 挂载点 / DOM mount point
  backgroundColor: "#1a1a2e", // 暗色背景 / Dark background
  scene: {
    create: function (this: Phaser.Scene) {
      // 占位文字——后续替换为 GameScene / Placeholder text — to be replaced by GameScene
      this.add.text(480, 320, "AIGameWorld", {
        fontFamily: "Segoe UI, sans-serif",
        fontSize: "32px",
        color: "#ffffff",
      }).setOrigin(0.5);
    },
  },
};

// 启动游戏 / Start the game
new Phaser.Game(config);
