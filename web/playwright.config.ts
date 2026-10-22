import os from "node:os";
import path from "node:path";
import { defineConfig, devices } from "@playwright/test";

/**
 * End-to-end tests: a real browser (the Microsoft Edge already installed on this machine, so nothing is downloaded), a real API, a real engine.
 * They run on their own ports (API 8110, web 5180) against a throwaway database, so they never touch a family's data or a dev server you have open.
 *
 *   npm run e2e            run them (headless)
 *   npm run e2e -- --headed   watch them
 */
const API_PORT = 8110;
const WEB_PORT = 5180;
const PREVIEW_PORT = 5181;
const DB = path.join(os.tmpdir(), "fo-e2e.db");
const ROOT = path.resolve(import.meta.dirname, "..");

export default defineConfig({
  testDir: "./e2e",
  timeout: 90_000,
  expect: { timeout: 15_000 },
  fullyParallel: false, // the allocation model is one shared thread: kinder to run one test at a time
  workers: 1,
  retries: 0,
  reporter: [["list"]],
  use: {
    baseURL: `http://127.0.0.1:${WEB_PORT}`,
    channel: "msedge",
    trace: "off",
    screenshot: "off",
    actionTimeout: 15_000,
  },
  projects: [{ name: "desktop", use: { ...devices["Desktop Chrome"], channel: "msedge" } }],
  webServer: [
    {
      command: `"${path.join(ROOT, ".venv", "Scripts", "python.exe")}" -B -c "import os,pathlib;p=pathlib.Path(os.environ['FO_DB_PATH']);[f.unlink() for f in p.parent.glob(p.name+'*') if f.is_file()]" && "${path.join(ROOT, ".venv", "Scripts", "python.exe")}" -B -m uvicorn api.main:app --app-dir "${ROOT}" --host 127.0.0.1 --port ${API_PORT}`,
      url: `http://127.0.0.1:${API_PORT}/api/health`,
      env: { FO_DB_PATH: DB, FO_API_CORS_ORIGINS: `http://127.0.0.1:${WEB_PORT}` },
      reuseExistingServer: false,
      timeout: 120_000,
    },
    {
      command: `node "${path.join(import.meta.dirname, "node_modules", "vite", "bin", "vite.js")}" --port ${WEB_PORT} --strictPort --host 127.0.0.1`,
      url: `http://127.0.0.1:${WEB_PORT}`,
      env: { FO_API_URL: `http://127.0.0.1:${API_PORT}` },
      reuseExistingServer: false,
      timeout: 120_000,
    },
    {
      // The built app, served with the production security headers (security-headers.ts), for e2e/csp.spec.ts.
      command: `node "${path.join(import.meta.dirname, "node_modules", "vite", "bin", "vite.js")}" build && node "${path.join(import.meta.dirname, "node_modules", "vite", "bin", "vite.js")}" preview --port ${PREVIEW_PORT} --strictPort --host 127.0.0.1`,
      url: `http://127.0.0.1:${PREVIEW_PORT}`,
      env: { FO_API_URL: `http://127.0.0.1:${API_PORT}` },
      reuseExistingServer: false,
      timeout: 180_000,
    },
  ],
});
