/**
 * Vite build/dev configuration for the client app.
 */

import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';
export default defineConfig({
  plugins: [react()],
  server: {
    port: 3001,
    strictPort: true,
    host: process.env.VITE_HOST || '127.0.0.1',
    watch: {
      usePolling: true,
      interval: 300
    }
  }
});
