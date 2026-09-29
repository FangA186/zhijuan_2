import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';
import { projectOverviewPlugin } from './projectOverviewPlugin';

// https://vite.dev/config/
export default defineConfig({
  plugins: [react(), projectOverviewPlugin()],
  server: {
    port: 3000,
    open: false,
    proxy: {
      '/v1': {
        target: 'http://127.0.0.1:8000',
        changeOrigin: true,
      },
    },
  },
  build: {
    rollupOptions: {
      output: {
        manualChunks: {
          katex: ['katex'],
          react: ['react', 'react-dom'],
          lucide: ['lucide-react'],
        },
      },
    },
  },
});
