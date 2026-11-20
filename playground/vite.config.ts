import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

export default defineConfig({
    plugins: [react()],
    server: {
        port: 5173,
        proxy: {
            // 和 tone-front 的 config/proxy.ts 一样：把 /api/assistant 转发给 RAG 后端
            '/api/assistant': {
                target: process.env.ASSISTANT_API || 'http://127.0.0.1:8000',
                changeOrigin: true,
            },
        },
    },
});
