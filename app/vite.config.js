import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { defineConfig } from 'vite';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const repoRoot = path.resolve(__dirname, '..');

// Pose data and rigs are baked into the bundle through import.meta.glob in
// src/main.js, so the built app needs no live middleware.
export default defineConfig({
  root: __dirname,
  // GitHub Pages serves the repo at /pose-library/; PAGES_BASE=/ restores
  // root-relative asset URLs for local/legacy serving.
  base: process.env.PAGES_BASE ?? '/pose-library/',
  assetsInclude: ['**/*.glb'],
  server: {
    fs: {
      allow: [repoRoot],
    },
  },
  preview: {
    port: 4173,
    strictPort: true,
  },
});
