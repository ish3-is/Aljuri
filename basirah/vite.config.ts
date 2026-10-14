import tailwindcss from '@tailwindcss/vite'
import react from '@vitejs/plugin-react'
import { defineConfig } from 'vite'

// A relative base keeps the build deployable to any GitHub Pages path
// (project site `/basirah/`, a custom domain, or a local preview) without
// hardcoding a root-only asset prefix. Vite rewrites every emitted asset
// URL at build time, including hashed bundles.
export default defineConfig({
  base: './',
  plugins: [react(), tailwindcss()],

   server: {
    port: 5199,
    strictPort: true,

    proxy: {
      '/api': {
        target: 'http://127.0.0.1:8000',
        changeOrigin: true,
        secure: false,
      },
    },
  },

  build: {
    /**
     * The only chunk above the default 500 kB advisory is the Excel
     * workbook writer (~930 kB), which is reached exclusively through a
     * dynamic import from `exportExcel.ts` and is never part of the
     * initial load. Raising the limit removes a warning that no longer
     * describes a real problem — it does not hide a regression, because
     * the entry chunk is still checked by this build's own output.
     */
    chunkSizeWarningLimit: 1000,
  },
})