import react from "@vitejs/plugin-react";
import { loadEnv } from "vite";
import { defineConfig } from "vitest/config";
import { SECURITY_HEADERS } from "./security-headers";

// The dev server proxies /api to the FastAPI backend, so the browser sees one origin and the
// sign-in cookie works without any CORS exceptions. Port 8100: 8000 is taken on this machine.
// Override with FO_API_URL (environment or web/.env.local) if the API runs elsewhere.
export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, ".", "FO_");
  return {
    plugins: [react()],
    server: {
      port: 5173,
      strictPort: true,
      proxy: { "/api": { target: env.FO_API_URL ?? "http://127.0.0.1:8100", changeOrigin: false } },
    },
    // `vite preview` serves the built app with the production security headers, so they can be tested (e2e/csp.spec.ts).
    preview: { port: 5181, strictPort: true, headers: SECURITY_HEADERS, proxy: { "/api": { target: env.FO_API_URL ?? "http://127.0.0.1:8100", changeOrigin: false } } },
    build: { sourcemap: false },
    test: {
      environment: "jsdom",
      globals: true,
      setupFiles: ["./src/test/setup.ts"],
      include: ["src/**/*.test.{ts,tsx}"], // the browser tests in e2e/ are Playwright's, not vitest's
      testTimeout: 20_000, // whole-app renders and axe audits are slow when the files run in parallel; this only lengthens the wait
      css: { include: [/tokens\.css/] }, // only the tokens file is read (by the contrast test); other CSS stays blank
    },
  };
});
