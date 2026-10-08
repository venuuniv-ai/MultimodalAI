import { defineConfig } from '@playwright/test';
import { fileURLToPath } from 'node:url';
export default defineConfig({
  testDir: './tests', workers: 1, timeout: 30000,
  use: {baseURL:'http://127.0.0.1:8010', viewport:{width:1280,height:900}},
  webServer: {
    command: '.venv/bin/python -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8010',
    cwd: fileURLToPath(new URL('..', import.meta.url)),
    url: 'http://127.0.0.1:8010/api/health', reuseExistingServer:false,
    env: {RESEARCH_DESK_DB:'.logs/browser-test.sqlite3'}, timeout:30000
  }
});
