import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  server: {
    port: 3001,
    strictPort: true,
    host: process.env.VITE_HOST || '127.0.0.1',
    // Polling avoids ENOSPC when the host has a low inotify watcher limit.
    watch: {
      usePolling: true,
      interval: 300,
    },
  },
})
