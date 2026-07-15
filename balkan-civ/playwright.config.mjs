import { defineConfig } from "@playwright/test";

export default defineConfig({
  testDir: "./e2e",
  fullyParallel: false,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 1 : 0,
  timeout: 45_000,
  expect: { timeout: 8_000 },
  reporter: process.env.CI ? [["github"], ["line"]] : "line",
  use: {
    baseURL: "http://127.0.0.1:4173",
    headless: true,
    screenshot: "only-on-failure",
    trace: "retain-on-failure",
    launchOptions: {
      args: ["--enable-webgl", "--ignore-gpu-blocklist", "--use-gl=swiftshader",
        "--disable-features=WebRtcHideLocalIpsWithMdns"],
    },
  },
  webServer: {
    command: "python3 -m http.server 4173 --bind 127.0.0.1",
    url: "http://127.0.0.1:4173/index.html",
    reuseExistingServer: !process.env.CI,
    timeout: 30_000,
  },
  projects: [
    { name: "chromium-desktop", use: { viewport: { width: 1440, height: 900 } } },
    { name: "chromium-mobile", use: { viewport: { width: 390, height: 844 }, hasTouch: true, isMobile: true } },
  ],
});
