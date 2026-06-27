/** SimGameWorld frontend entry point. */
import Phaser from "phaser";

const config: Phaser.Types.Core.GameConfig = {
  type: Phaser.AUTO,
  width: 960,
  height: 640,
  parent: "game",
  backgroundColor: "#1a1a2e",
  scene: {
    create: function (this: Phaser.Scene) {
      this.add.text(480, 320, "SimGameWorld", {
        fontFamily: "Segoe UI, sans-serif",
        fontSize: "32px",
        color: "#ffffff",
      }).setOrigin(0.5);
    },
  },
};

new Phaser.Game(config);
