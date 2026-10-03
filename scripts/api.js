#!/usr/bin/env node
// Cross-platform launcher for the FastAPI dev server (`npm run api`).
const { spawnSync } = require("child_process");
const path = require("path");

const candidates = process.platform === "win32" ? ["python", "python3"] : ["python3", "python"];
const backendDir = path.join(__dirname, "..", "backend");

function tryRun(cmd) {
  const result = spawnSync(cmd, ["--version"], { stdio: "ignore" });
  return result.status === 0;
}

const python = candidates.find(tryRun);
if (!python) {
  console.error("No Python interpreter found on PATH (tried: " + candidates.join(", ") + ").");
  process.exit(1);
}

const run = spawnSync(
  python,
  ["-m", "uvicorn", "app.main:app", "--reload", "--port", "8000"],
  { stdio: "inherit", cwd: backendDir }
);
process.exit(run.status === null ? 1 : run.status);
