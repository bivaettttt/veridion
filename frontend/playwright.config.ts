import { defineConfig } from "@playwright/test";

export default defineConfig({
  testDir: "./tests",
  timeout: 90_000,
  expect: { timeout: 20_000 },
  use: {
    baseURL: process.env.VERIDION_WEB_URL || "http://127.0.0.1:3817",
    viewport: { width: 1440, height: 1000 },
  },
});
