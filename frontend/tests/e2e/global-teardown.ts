/** E2E 全局清理：结束后端服务.
 * Global teardown: stop backend service.
 */
import { exec } from "child_process";
import fs from "fs";
import os from "os";
import path from "path";
import { fileURLToPath } from "url";

const __dirname = path.dirname(fileURLToPath(import.meta.url));

function killProcessTree(pid: number): Promise<void> {
  return new Promise((resolve) => {
    const isWin = os.platform() === "win32";
    const cmd = isWin ? `taskkill /PID ${pid} /T /F` : `kill -9 ${pid}`;
    exec(cmd, () => resolve());
  });
}

export default async function globalTeardown(): Promise<void> {
  const pidFile = path.join(__dirname, ".backend.pid");
  if (!fs.existsSync(pidFile)) return;

  const pid = Number(fs.readFileSync(pidFile, "utf-8").trim());
  try {
    await killProcessTree(pid);
  } catch {
    // 进程可能已经退出 / Process may already be gone
  }
  fs.unlinkSync(pidFile);
  // 等待文件句柄释放 / Wait for file handles to release
  await new Promise((r) => setTimeout(r, 1000));
  console.log("[e2e teardown] backend stopped");
}
