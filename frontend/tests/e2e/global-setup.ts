/** E2E 全局启动：启动后端服务（mock LLM + 独立 DB）.
 * Global setup: start backend service (mock LLM + isolated DB).
 */
import { exec, spawn } from "child_process";
import fs from "fs";
import os from "os";
import path from "path";
import { fileURLToPath } from "url";

const BACKEND_PORT = 8000;
const HEALTH_URL = `http://localhost:${BACKEND_PORT}/health`;
const SETUP_TIMEOUT_MS = 120_000;
const __dirname = path.dirname(fileURLToPath(import.meta.url));

function killExistingBackend(): Promise<void> {
  return new Promise((resolve) => {
    const isWin = os.platform() === "win32";
    const findPidCmd = isWin
      ? `for /f "tokens=5" %a in ('netstat -ano ^| findstr :${BACKEND_PORT}') do @taskkill /PID %a /T /F`
      : `lsof -ti :${BACKEND_PORT} | xargs kill -9`;
    exec(findPidCmd, () => {
      // 等待进程释放文件句柄 / Wait for process to release file handles
      setTimeout(resolve, 1500);
    });
  });
}

async function waitForBackend(): Promise<void> {
  const start = Date.now();
  while (Date.now() - start < SETUP_TIMEOUT_MS) {
    try {
      const res = await fetch(HEALTH_URL);
      if (res.ok) return;
    } catch {
      // 后端还没起来 / backend not ready yet
    }
    await new Promise((r) => setTimeout(r, 500));
  }
  throw new Error("后端未在 120s 内就绪 / Backend did not become ready");
}

async function waitForWorldReady(): Promise<void> {
  const start = Date.now();
  const stateUrl = `http://localhost:${BACKEND_PORT}/api/world/mock_world/state`;
  while (Date.now() - start < SETUP_TIMEOUT_MS) {
    try {
      const res = await fetch(stateUrl);
      if (res.ok) {
        const data = (await res.json()) as { pcs?: unknown[] };
        if ((data.pcs?.length ?? 0) > 0) return;
      }
    } catch {
      // 状态接口还没好 / state endpoint not ready yet
    }
    await new Promise((r) => setTimeout(r, 500));
  }
  throw new Error("世界 mock_world 未在 120s 内准备就绪 / World mock_world did not become ready");
}

export default async function globalSetup(): Promise<void> {
  const backendDir = path.resolve(__dirname, "../../../backend");
  const pidFile = path.join(__dirname, ".backend.pid");

  // 先结束可能残留的后端进程 / Kill any leftover backend process first
  await killExistingBackend();

  // 清理上一次可能残留的 DB / Clean up leftover DB from previous run
  const dbPath = path.join(backendDir, "data", "e2e.db");
  if (fs.existsSync(dbPath)) {
    fs.unlinkSync(dbPath);
  }

  const backend = spawn(
    "uv",
    ["run", "uvicorn", "src.server:app", "--host", "0.0.0.0", "--port", String(BACKEND_PORT)],
    {
      cwd: backendDir,
      shell: true,
      env: {
        ...process.env,
        AIGW_CONFIG: path.resolve(backendDir, "..", "config.e2e.yaml"),
      },
      stdio: "pipe",
    }
  );

  if (!backend.pid) {
    throw new Error("后端进程启动失败 / Failed to start backend process");
  }

  fs.writeFileSync(pidFile, String(backend.pid));

  backend.stdout?.on("data", (data: Buffer) => {
    process.stdout.write(`[backend] ${data.toString()}`);
  });
  backend.stderr?.on("data", (data: Buffer) => {
    process.stderr.write(`[backend] ${data.toString()}`);
  });

  await waitForBackend();
  await waitForWorldReady();
  console.log("[e2e setup] backend ready");
}
