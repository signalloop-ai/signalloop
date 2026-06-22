import { defineConfig, devices } from "@playwright/test";

const baseURL = process.env.PLAYWRIGHT_BASE_URL ?? "http://127.0.0.1:3000";
const skipWebServer = process.env.PLAYWRIGHT_SKIP_WEBSERVER === "1";

export default defineConfig({
  testDir: "./tests/e2e",
  timeout: 30_000,
  expect: {
    timeout: 5_000,
  },
  use: {
    baseURL,
    trace: "retain-on-failure",
  },
  webServer: skipWebServer
    ? undefined
    : {
        command:
          "NEXT_PUBLIC_API_URL=http://127.0.0.1:8015 npm run dev -- -H 127.0.0.1 --port 3000",
        url: baseURL,
        reuseExistingServer: true,
        timeout: 60_000,
      },
  projects: [
    {
      name: "chromium",
      use: { ...devices["Desktop Chrome"] },
    },
  ],
});
