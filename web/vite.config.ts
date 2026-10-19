import react from "@vitejs/plugin-react";
import { loadEnv } from "vite";
import { defineConfig } from "vitest/config";

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
    build: { sourcemap: false },
    test: {
      environment: "jsdom",
      globals: true,
      setupFiles: ["./src/test/setup.ts"],
      css: { include: [/tokens\.css/] }, // only the tokens file is read (by the contrast test); other CSS stays blank
    },
  };
});
