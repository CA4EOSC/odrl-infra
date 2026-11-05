/* global process */
import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'
import path from 'path'
import { execSync } from 'child_process'

// Build version shown in the sidebar footer. Docker builds pass VITE_GIT_* as build args
// (the image has no .git); local builds read it from git.
const git = (cmd) => { try { return execSync(`git ${cmd}`, { stdio: ['ignore', 'pipe', 'ignore'] }).toString().trim() } catch { return '' } }
const BUILD_INFO = {
  commit: process.env.VITE_GIT_SHA || git('rev-parse HEAD'),
  branch: process.env.VITE_GIT_BRANCH || git('rev-parse --abbrev-ref HEAD'),
  date: process.env.VITE_GIT_DATE || git('log -1 --format=%cI'),
  dirty: process.env.VITE_GIT_SHA ? process.env.VITE_GIT_DIRTY === 'true' : git('status --porcelain --untracked-files=no') !== '',
  builtAt: new Date().toISOString(),
}

// https://vite.dev/config/
export default defineConfig({
  define: {
    __BUILD_INFO__: JSON.stringify(BUILD_INFO),
  },
  plugins: [
    tailwindcss(),
    react()
  ],
  // Tailwind v4 uses CSS variables for dark mode by default, 
  // but to use the manual toggle class strategy, we rely on the .dark class processing.
  // No explicit 'darkMode' config needed in vite.config.js for v4 if using @tailwindcss/vite 
  // as it detects usage. But for v3 compat or specific config, we might need tailwind.config.js.
  // Since we don't have tailwind.config.js, we assume v4 defaults.
  // v4 supports `dark:` variant out of the box.
  // The crucial part is adding 'dark' class to html element, which ThemeContext does.
  resolve: {
    alias: {
      "@": path.resolve(__dirname, "./src"),
    },
    extensions: ['.mjs', '.js', '.mts', '.ts', '.jsx', '.tsx', '.json']
  },
  server: {
    proxy: {
      '/api': {
        target: 'http://localhost:8001',
        changeOrigin: true,
      }
    }
  }
})
