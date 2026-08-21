import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'

// https://vite.dev/config/
export default defineConfig({
  plugins: [vue()],
  // 资源路径以 /static 为前缀，与 FastAPI app.mount("/static", StaticFiles(...)) 对齐
  base: '/static/',
  build: {
    // 构建产物输出到后端 src/static，由 FastAPI 统一托管（单端口部署）
    outDir: '../src/static',
    emptyOutDir: true,
  },
  server: {
    port: 5173,
    proxy: {
      // 开发环境代理到后端，避免跨域
      '/auth': 'http://localhost:426',
      '/chat': 'http://localhost:426',
      '/conversations': 'http://localhost:426',
    },
  },
})
