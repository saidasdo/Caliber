#!/usr/bin/env node
// Cross-platform launcher for the Python ingestion pipeline (Windows uses `python`,
// macOS/Linux typically only ship `python3`).
const { spawnSync } = require("child_process");
const path = require("path");

const candidates = process.platform === "win32" ? ["python", "python3"] : ["python3", "python"];
const scriptPath = path.join(__dirname, "..", "backend", "app", "ingest", "run.py");

function tryRun(cmd) {
  const result = spawnSync(cmd, ["--version"], { stdio: "ignore" });
  return result.status === 0;
}

const python = candidates.find(tryRun);
if (!python) {
  console.error("No Python interpreter found on PATH (tried: " + candidates.join(", ") + ").");
  process.exit(1);
}

const run = spawnSync(python, [scriptPath], { stdio: "inherit" });
process.exit(run.status === null ? 1 : run.status);
