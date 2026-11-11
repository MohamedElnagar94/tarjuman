// Runs the browser tests against a real Tarjuman server that needs no internet
// (backend/tests/e2e_server.py: fake translation and voices, one sample video).
// Usage: npm run e2e      env PYTHON=<python with the backend installed>  CHROME=<path to chrome>
import { spawn } from "node:child_process";
import { existsSync } from "node:fs";
import { dirname, join, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const here = dirname(fileURLToPath(import.meta.url));
const root = resolve(here, "..", "..");
const port = process.env.E2E_PORT || "4390";
const base = `http://127.0.0.1:${port}`;

function python() {
  if (process.env.PYTHON) return process.env.PYTHON;
  for (const p of [join(root, ".venv", "Scripts", "python.exe"), join(root, ".venv", "bin", "python")]) if (existsSync(p)) return p;
  return process.platform === "win32" ? "python" : "python3";
}

if (!existsSync(join(root, "frontend", "dist", "index.html"))) {
  console.error("frontend/dist is missing: run `npm run build` first.");
  process.exit(1);
}

const server = spawn(python(), [join(root, "backend", "tests", "e2e_server.py"), port], { stdio: ["ignore", "inherit", "inherit"] });
let finished = false;
server.on("exit", (code) => {
  if (!finished) {
    console.error(`The test server stopped early (exit ${code}).`);
    process.exit(1);
  }
});

async function ready() {
  for (let i = 0; i < 120; i++) {
    try {
      if ((await fetch(base + "/api/health")).ok) return;
    } catch {}
    await new Promise((r) => setTimeout(r, 500));
  }
  throw new Error("The test server did not answer within a minute.");
}

let code = 1;
try {
  await ready();
  const tests = spawn(process.execPath, ["--test", "--test-concurrency=1", join(here, "app.e2e.mjs")], {
    stdio: "inherit",
    env: { ...process.env, E2E_BASE: base },
  });
  code = await new Promise((r) => tests.on("exit", (c) => r(c ?? 1)));
} catch (e) {
  console.error(e.message);
} finally {
  finished = true;
  server.kill();
}
process.exit(code);
