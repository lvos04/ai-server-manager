import { defineConfig } from "vitest/config";
import path from "node:path";

export default defineConfig({
  resolve: { alias: { "@": path.resolve(import.meta.dirname, "src") } },
  test: {
    include: ["tests/unit/**/*.test.{ts,tsx,mjs}"],
    environment: "node",
    pool: "threads",
    maxWorkers: 2,
  },
});
