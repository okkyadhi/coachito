import path from 'path';

import react from '@vitejs/plugin-react';
import { defineConfig } from 'vite';
import { VitePWA } from 'vite-plugin-pwa';

export default defineConfig({
  plugins: [
    react(),
    VitePWA({
      registerType: 'autoUpdate',
      // PWA enabled in step 19
      selfDestroying: true,
      manifest: {
        name: 'Coachito',
        short_name: 'Coachito',
        description: 'Coachito — tu coach, en tu bolsillo. Padel skill assessment and progression tracking.',
        theme_color: '#C66B47',
        background_color: '#FBF6EC',
        display: 'standalone',
        start_url: '/',
        icons: [],
      },
    }),
  ],
  resolve: {
    alias: {
      '@': path.resolve(__dirname, './src'),
    },
  },
  server: {
    host: '0.0.0.0',
    port: 5173,
    proxy: {
      // FE calls /api/auth/... → BE serves /auth/... (the prefix is stripped).
      // In Docker the api service is reachable as "api"; on bare-host dev set
      // VITE_API_PROXY_TARGET=http://localhost:8002 in your shell.
      '/api': {
        target: process.env.VITE_API_PROXY_TARGET ?? 'http://api:8000',
        changeOrigin: true,
        rewrite: (p) => p.replace(/^\/api/, ''),
      },
      // /i/{token} is the public invite landing page served by the API as
      // HTML.  Use a regex matcher (key prefix is ^…) so SPA routes like
      // /invite/:token aren't accidentally forwarded to the API.
      '^/i/': {
        target: process.env.VITE_API_PROXY_TARGET ?? 'http://api:8000',
        changeOrigin: true,
      },
    },
  },
});
