import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import vueDevTools from 'vite-plugin-vue-devtools'

export default defineConfig({
  plugins: [vueDevTools(),vue()],
  server: {
    host: '127.0.0.1',
    port: 5173,
    strictPort: false,
    hmr: {
      host: '127.0.0.1',
      protocol: 'ws'
    }
  }
})
