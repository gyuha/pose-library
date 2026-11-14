import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { defineConfig } from 'vite';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const repoRoot = path.resolve(__dirname, '..');

// Pose data and rigs are baked into the bundle through import.meta.glob in
// src/main.js, so the built app needs no live middleware.
export default defineConfig({
  root: __dirname,
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
