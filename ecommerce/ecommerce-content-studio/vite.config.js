import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  server: {
    port: Number(process.env.FRONTEND_PORT || 5173),
    strictPort: true,
    proxy: {
      '/api': process.env.API_TARGET || 'http://localhost:8790',
      '/uploads': process.env.API_TARGET || 'http://localhost:8790',
      '/generated': process.env.API_TARGET || 'http://localhost:8790'
    }
  },
  build: { outDir: 'dist' }
})
