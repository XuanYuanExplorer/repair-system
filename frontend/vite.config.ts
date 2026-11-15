import { fileURLToPath, URL } from 'node:url'
import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'

export default defineConfig({
  plugins: [vue()],
  resolve: { alias: { '@': fileURLToPath(new URL('./src', import.meta.url)) } },
  server: {
    port: 5173,
    host: '0.0.0.0',
    proxy: { '/api': { target: 'http://127.0.0.1:8000', changeOrigin: true },
             '/uploads': { target: 'http://127.0.0.1:8000', changeOrigin: true } },
  },
  build: {
    target: 'es2018',
    cssCodeSplit: true,
    chunkSizeWarningLimit: 900,
    rollupOptions: {
      output: {
        manualChunks: { vendor: ['vue', 'vue-router', 'pinia', 'axios'] },
        chunkFileNames: 'assets/[name]-[hash].js',
      },
    },
  },
})
