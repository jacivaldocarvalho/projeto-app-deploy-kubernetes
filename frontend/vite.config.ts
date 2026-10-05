import { defineConfig } from 'vitest/config'
import react from '@vitejs/plugin-react'
export default defineConfig({
  plugins: [react()],
  server: { proxy: { '/index.php': 'http://127.0.0.1:8080', '/health.php': 'http://127.0.0.1:8080' } },
  test: { include: ['src/**/*.test.tsx'], environment: 'jsdom', setupFiles: ['./src/test-setup.ts'] },
})
