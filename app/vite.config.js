import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { defineConfig } from 'vite';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const repoRoot = path.resolve(__dirname, '..');
const posesDir = path.resolve(repoRoot, 'poses');

function readLivePosesPayload() {
  const files = fs
    .readdirSync(posesDir)
    .filter((f) => /^pose_.*\.json$/.test(f))
    .sort();
  const poses = {};
  for (const file of files) {
    const raw = JSON.parse(fs.readFileSync(path.join(posesDir, file), 'utf8'));
    if (raw && raw.meta && 'sourceImage' in raw.meta) {
      delete raw.meta.sourceImage;
    }
    const id = raw?.meta?.id || file.replace(/\.json$/, '');
    poses[id] = raw;
  }
  let catalog = { formatVersion: 1, poses: [] };
  const catalogPath = path.join(posesDir, 'catalog.ko.json');
  if (fs.existsSync(catalogPath)) {
    catalog = JSON.parse(fs.readFileSync(catalogPath, 'utf8'));
  }
  return { poses, catalog };
}

function attachPoseSyncMiddleware(middlewares) {
  middlewares.use('/__pose_sync.json', (req, res, next) => {
    if (req.method !== 'GET') return next();
    try {
      const payload = readLivePosesPayload();
      res.setHeader('Content-Type', 'application/json; charset=utf-8');
      res.setHeader('Cache-Control', 'no-store');
      res.end(JSON.stringify(payload));
    } catch {
      next();
    }
  });
}

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
  plugins: [
    {
      name: 'pose-library-live-sync',
      configureServer(server) {
        attachPoseSyncMiddleware(server.middlewares);
      },
      configurePreviewServer(server) {
        attachPoseSyncMiddleware(server.middlewares);
      },
    },
  ],
});
