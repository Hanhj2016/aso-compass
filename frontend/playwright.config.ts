import { defineConfig, devices } from "@playwright/test";

export default defineConfig({
  testDir: "./e2e",
  fullyParallel: true,
  reporter: "line",
  use: { baseURL: "http://127.0.0.1:5173", trace: "retain-on-failure" },
  webServer: [
    {
      command: "npm run dev",
      url: "http://127.0.0.1:5173",
      reuseExistingServer: true,
      timeout: 30_000,
    },
    {
      command:
        "cd ../backend && rm -f /tmp/aso_compass_e2e.db && DATABASE_URL=sqlite:////tmp/aso_compass_e2e.db python -m alembic upgrade head && DATABASE_URL=sqlite:////tmp/aso_compass_e2e.db APP_ENV=test RUN_WORKER_ENABLED=false AI_ENABLED=false CREATE_RUN_RATE_LIMIT_PER_MINUTE=1000 FRONTEND_ORIGINS=http://127.0.0.1:5173 python -m uvicorn app.main:app --host 127.0.0.1 --port 8100",
      url: "http://127.0.0.1:8100/health/ready",
      reuseExistingServer: true,
      timeout: 30_000,
    },
  ],
  projects: [
    { name: "desktop", use: { ...devices["Desktop Chrome"] } },
    { name: "mobile", use: { ...devices["Pixel 7"] } },
  ],
});
