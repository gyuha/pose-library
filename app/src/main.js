import * as THREE from 'three';
import { GLTFLoader } from 'three/examples/jsm/loaders/GLTFLoader.js';
import { OrbitControls } from 'three/examples/jsm/controls/OrbitControls.js';
import { buildPosePrompt, ANGLE_PRESETS } from '../../prompt/index.js';

// 1. Eager glob imports (excluding poses/reference/**)
const rawPoseModules = import.meta.glob(
  ['../../poses/pose_*.json', '!../../poses/reference/**'],
  { eager: true, import: 'default' }
);
const rawCatalogModules = import.meta.glob('../../poses/catalog.ko.json', {
  eager: true,
  import: 'default',
});
const glbUrlModules = import.meta.glob('../../rig/*.glb', {
  eager: true,
  query: '?url',
  import: 'default',
});

function sanitizePose(raw) {
  const copy = structuredClone(raw);
  if (copy && copy.meta && 'sourceImage' in copy.meta) {
    delete copy.meta.sourceImage;
  }
  return copy;
}

const posesMap = new Map();
for (const [filePath, raw] of Object.entries(rawPoseModules)) {
  if (filePath.includes('/reference/')) continue;
  const pose = sanitizePose(raw);
  const id =
    pose?.meta?.id ||
    filePath
      .split('/')
      .pop()
      .replace(/\.json$/, '');
  posesMap.set(id, pose);
}

const catalogMap = new Map();
for (const rawCatalog of Object.values(rawCatalogModules)) {
  if (rawCatalog && Array.isArray(rawCatalog.poses)) {
    for (const entry of rawCatalog.poses) {
      if (entry && entry.id) {
        catalogMap.set(entry.id, entry);
      }
    }
  }
}

function getGlbUrl(gender) {
  for (const [pathKey, url] of Object.entries(glbUrlModules)) {
    if (pathKey.endsWith(`/${gender}.glb`)) return url;
  }
  throw new Error(`GLB URL not found for gender: ${gender}`);
}

function getPoseIdsSorted() {
  return Array.from(posesMap.keys()).sort();
}

function getCatalogEntryForPose(poseId) {
  const existing = catalogMap.get(poseId);
  if (existing) return existing;
  const pose = posesMap.get(poseId);
  return {
    id: poseId,
    name: pose?.meta?.name || poseId,
    tags: [],
    description: pose?.meta?.description || pose?.meta?.name || poseId,
  };
}

// 2. Constants & Camera Setup
const BG_COLOR_HEX = 0xf6f7f9;
const EXPORT_WIDTH = 900;
const EXPORT_HEIGHT = 1200;
const THUMB_WIDTH = 240;
const THUMB_HEIGHT = 320;
const CAMERA_FOV = 26;
const CAMERA_DISTANCE = 5.3;
const CAMERA_TARGET = new THREE.Vector3(0, 0.96, 0);
const CATEGORY_ORDER = ['서기', '앉기', '동작'];

// 3. State
const state = {
  poseId: getPoseIdsSorted()[0] || '',
  gender: 'female',
  angle: 'front',
  tagFilter: '',
};

// Rig storage: gender -> { root, bones, boneMap, restMap, hipsHeight, skinnedMeshes }
const rigs = {};
// Thumbnail cache: `${gender}:${poseId}` -> HTMLCanvasElement
const thumbCache = new Map();

// 4. Three.js Scene & Renderers
const scene = new THREE.Scene();
scene.background = new THREE.Color(BG_COLOR_HEX);

const ambientLight = new THREE.AmbientLight(0xffffff, 0.62);
scene.add(ambientLight);

const hemiLight = new THREE.HemisphereLight(0xffffff, 0xd8dde6, 0.42);
hemiLight.position.set(0, 4, 0);
scene.add(hemiLight);

const keyLight = new THREE.DirectionalLight(0xffffff, 0.8);
scene.add(keyLight);

const fillLight = new THREE.DirectionalLight(0xeef2f9, 0.32);
scene.add(fillLight);

const mainCanvas = document.getElementById('main-canvas');
const viewportContainer = document.getElementById('viewport-container');

const mainRenderer = new THREE.WebGLRenderer({
  canvas: mainCanvas,
  antialias: true,
  preserveDrawingBuffer: true,
  powerPreference: 'high-performance',
});
mainRenderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 2));
mainRenderer.outputColorSpace = THREE.SRGBColorSpace;

const offscreenRenderer = new THREE.WebGLRenderer({
  antialias: true,
  preserveDrawingBuffer: true,
  powerPreference: 'high-performance',
});
offscreenRenderer.setPixelRatio(1);
offscreenRenderer.outputColorSpace = THREE.SRGBColorSpace;

const camera = new THREE.PerspectiveCamera(CAMERA_FOV, 3 / 4, 0.1, 100);
const offscreenCamera = new THREE.PerspectiveCamera(CAMERA_FOV, 3 / 4, 0.1, 100);

const controls = new OrbitControls(camera, mainCanvas);
controls.enableDamping = false;
controls.target.copy(CAMERA_TARGET);
controls.minDistance = 1.2;
controls.maxDistance = 18.0;
controls.maxPolarAngle = Math.PI * 0.95;
controls.minPolarAngle = Math.PI * 0.05;

function syncLightsToCamera(refCam = camera) {
  refCam.updateMatrixWorld(true);
  const right = new THREE.Vector3();
  const up = new THREE.Vector3();
  const back = new THREE.Vector3();
  refCam.matrixWorld.extractBasis(right, up, back);

  keyLight.position
    .copy(CAMERA_TARGET)
    .addScaledVector(right, -2.2)
    .addScaledVector(up, 3.4)
    .addScaledVector(back, 4.6);

  fillLight.position
    .copy(CAMERA_TARGET)
    .addScaledVector(right, 3.0)
    .addScaledVector(up, 1.2)
    .addScaledVector(back, 3.2);
}

function positionCameraForPreset(cam, targetVec, presetKey) {
  const preset = ANGLE_PRESETS[presetKey];
  const yawRad = (preset.yawDeg * Math.PI) / 180;
  const pitchRad = (preset.pitchDeg * Math.PI) / 180;
  const dist = CAMERA_DISTANCE;
  const horiz = dist * Math.cos(pitchRad);

  cam.position.set(
    targetVec.x - horiz * Math.sin(yawRad),
    targetVec.y + dist * Math.sin(pitchRad),
    targetVec.z + horiz * Math.cos(yawRad)
  );
  cam.up.set(0, 1, 0);
  cam.lookAt(targetVec);
  cam.updateProjectionMatrix();
  cam.updateMatrixWorld(true);
}

function computeCameraAngles() {
  const dx = camera.position.x - controls.target.x;
  const dy = camera.position.y - controls.target.y;
  const dz = camera.position.z - controls.target.z;
  const len = Math.hypot(dx, dy, dz) || 1;

  let yawDeg = (Math.atan2(-dx, dz) * 180) / Math.PI;
  if (yawDeg <= -180) yawDeg += 360;
  if (Object.is(yawDeg, -0) || Math.abs(yawDeg) < 1e-12) yawDeg = 0;

  const sinPitch = Math.max(-1, Math.min(1, dy / len));
  let pitchDeg = (Math.asin(sinPitch) * 180) / Math.PI;
  if (Object.is(pitchDeg, -0) || Math.abs(pitchDeg) < 1e-12) pitchDeg = 0;

  return { yawDeg, pitchDeg };
}

function findNearestPresetKey() {
  const { yawDeg, pitchDeg } = computeCameraAngles();
  let bestKey = 'front';
  let bestDist = Infinity;
  for (const [key, preset] of Object.entries(ANGLE_PRESETS)) {
    const dyaw = ((yawDeg - preset.yawDeg + 540) % 360) - 180;
    const dpitch = pitchDeg - preset.pitchDeg;
    const dist = Math.hypot(dyaw, dpitch);
    if (dist < bestDist) {
      bestDist = dist;
      bestKey = key;
    }
  }
  return bestKey;
}

function renderMain() {
  syncLightsToCamera(camera);
  mainRenderer.render(scene, camera);
}

function resizeViewport() {
  if (!viewportContainer) return;
  const w = Math.max(1, viewportContainer.clientWidth);
  const h = Math.max(1, viewportContainer.clientHeight);
  camera.aspect = w / h;
  camera.updateProjectionMatrix();
  mainRenderer.setSize(w, h, false);
  renderMain();
}

// 5. Rig Loading & Pose Application
const gltfLoader = new GLTFLoader();

function loadRig(gender) {
  const url = getGlbUrl(gender);
  return new Promise((resolve, reject) => {
    gltfLoader.load(
      url,
      (gltf) => {
        const root = gltf.scene;
        root.position.set(0, 0, 0);
        root.quaternion.set(0, 0, 0, 1);
        root.scale.set(1, 1, 1);

        const skinnedMeshes = [];
        root.traverse((obj) => {
          if (obj.isMesh || obj.isSkinnedMesh) {
            obj.frustumCulled = false;
            const mats = Array.isArray(obj.material) ? obj.material : [obj.material];
            const replaced = mats.map((m) => {
              const isJoints = m && m.name === 'Joints';
              return new THREE.MeshStandardMaterial({
                name: m?.name || 'MannequinMat',
                color: isJoints ? 0x5c626b : 0xcfcac4,
                roughness: isJoints ? 0.82 : 0.74,
                metalness: 0.04,
                flatShading: true,
                side: THREE.DoubleSide,
              });
            });
            obj.material = Array.isArray(obj.material) ? replaced : replaced[0];
          }
          if (obj.isSkinnedMesh) {
            skinnedMeshes.push(obj);
          }
        });

        if (skinnedMeshes.length === 0) {
          reject(new Error(`No SkinnedMesh found in ${gender}.glb`));
          return;
        }

        const primarySkeleton = skinnedMeshes[0].skeleton;
        const bones = primarySkeleton.bones;
        const boneMap = new Map();
        const restMap = new Map();

        for (const bone of bones) {
          boneMap.set(bone.name, bone);
          restMap.set(bone.name, {
            p: bone.position.clone(),
            q: bone.quaternion.clone(),
          });
        }

        const pelvisRest = restMap.get('pelvis');
        const hipsHeight = pelvisRest ? pelvisRest.p.y : 0.866649;

        root.updateMatrixWorld(true);
        for (const sm of skinnedMeshes) {
          sm.skeleton.update();
        }

        resolve({
          gender,
          root,
          bones,
          boneMap,
          restMap,
          hipsHeight,
          skinnedMeshes,
        });
      },
      undefined,
      (err) => reject(err)
    );
  });
}

function applyPoseToRig(rig, pose) {
  if (!rig || !pose) return;
  const { bones, boneMap, restMap, hipsHeight, root, skinnedMeshes } = rig;

  for (const bone of bones) {
    const r = restMap.get(bone.name);
    bone.position.copy(r.p);
    bone.quaternion.copy(r.q);
    const entry = pose.bones?.[bone.name];
    if (entry && Array.isArray(entry.quaternion)) {
      const [qx, qy, qz, qw] = entry.quaternion;
      const pq = new THREE.Quaternion(qx, qy, qz, qw);
      bone.quaternion.multiply(pq);
    }
    bone.updateMatrix();
  }

  const pelvis = boneMap.get('pelvis');
  const pelvisRest = restMap.get('pelvis');
  const t = pose.root?.translation || [0, 0, 0];
  if (pelvis && pelvisRest) {
    pelvis.position.set(
      pelvisRest.p.x + t[0] * hipsHeight,
      pelvisRest.p.y + t[1] * hipsHeight,
      pelvisRest.p.z + t[2] * hipsHeight
    );
    pelvis.updateMatrix();
  }

  root.updateMatrixWorld(true);
  for (const sm of skinnedMeshes) {
    sm.skeleton.update();
  }
}

function setActiveRigVisibility(gender) {
  for (const [g, rig] of Object.entries(rigs)) {
    rig.root.visible = g === gender;
  }
}

function computeJointPositions(gender = state.gender) {
  const rig = rigs[gender];
  if (!rig) return {};
  rig.root.updateMatrixWorld(true);
  const out = {};
  const v = new THREE.Vector3();
  for (const bone of rig.bones) {
    v.setFromMatrixPosition(bone.matrixWorld);
    out[bone.name] = [v.x, v.y, v.z];
  }
  return out;
}

// 6. Prompt Computation
function getPromptText() {
  const pose = posesMap.get(state.poseId);
  if (!pose) return '';
  const catalogEntry = getCatalogEntryForPose(state.poseId);
  return buildPosePrompt({
    pose,
    catalogEntry,
    gender: state.gender,
    angle: state.angle,
  });
}

// 7. Offscreen Thumbnail & PNG Rendering
function renderThumbnailForPose(gender, poseId) {
  const cacheKey = `${gender}:${poseId}`;
  if (thumbCache.has(cacheKey)) {
    return thumbCache.get(cacheKey);
  }

  const rig = rigs[gender];
  const pose = posesMap.get(poseId);
  if (!rig || !pose) return null;

  setActiveRigVisibility(gender);
  applyPoseToRig(rig, pose);

  offscreenRenderer.setSize(THUMB_WIDTH, THUMB_HEIGHT, false);
  offscreenCamera.aspect = THUMB_WIDTH / THUMB_HEIGHT;
  positionCameraForPreset(offscreenCamera, CAMERA_TARGET, 'front');
  syncLightsToCamera(offscreenCamera);
  offscreenRenderer.render(scene, offscreenCamera);

  const cachedCanvas = document.createElement('canvas');
  cachedCanvas.width = THUMB_WIDTH;
  cachedCanvas.height = THUMB_HEIGHT;
  const ctx = cachedCanvas.getContext('2d');
  ctx.drawImage(offscreenRenderer.domElement, 0, 0);

  thumbCache.set(cacheKey, cachedCanvas);
  return cachedCanvas;
}

function renderAllThumbnailsForGender(gender) {
  const ids = getPoseIdsSorted();
  for (const id of ids) {
    const srcCanvas = renderThumbnailForPose(gender, id);
    const card = document.querySelector(`[data-pose-id="${id}"]`);
    if (card && srcCanvas) {
      const dstCanvas = card.querySelector('canvas.pose-thumb-canvas');
      if (dstCanvas) {
        const ctx = dstCanvas.getContext('2d');
        ctx.clearRect(0, 0, dstCanvas.width, dstCanvas.height);
        ctx.drawImage(srcCanvas, 0, 0, dstCanvas.width, dstCanvas.height);
      }
    }
  }

  // Restore active gender & pose after thumbnail pass
  setActiveRigVisibility(state.gender);
  const currentPose = posesMap.get(state.poseId);
  if (currentPose && rigs[state.gender]) {
    applyPoseToRig(rigs[state.gender], currentPose);
  }
  syncLightsToCamera(camera);
}

function renderExportPngDataUrl() {
  const rig = rigs[state.gender];
  const pose = posesMap.get(state.poseId);
  if (rig && pose) {
    setActiveRigVisibility(state.gender);
    applyPoseToRig(rig, pose);
  }

  offscreenRenderer.setSize(EXPORT_WIDTH, EXPORT_HEIGHT, false);
  offscreenCamera.fov = camera.fov;
  offscreenCamera.aspect = EXPORT_WIDTH / EXPORT_HEIGHT;
  offscreenCamera.position.copy(camera.position);
  offscreenCamera.quaternion.copy(camera.quaternion);
  offscreenCamera.up.copy(camera.up);
  offscreenCamera.updateProjectionMatrix();
  offscreenCamera.updateMatrixWorld(true);

  syncLightsToCamera(offscreenCamera);
  offscreenRenderer.render(scene, offscreenCamera);

  const dataUrl = offscreenRenderer.domElement.toDataURL('image/png');
  syncLightsToCamera(camera);
  return dataUrl;
}

function dataUrlToBlob(dataUrl) {
  const [header, base64] = dataUrl.split(',');
  const mimeMatch = header.match(/:(.*?);/);
  const mime = mimeMatch ? mimeMatch[1] : 'image/png';
  const binary = atob(base64);
  const bytes = new Uint8Array(binary.length);
  for (let i = 0; i < binary.length; i++) {
    bytes[i] = binary.charCodeAt(i);
  }
  return new Blob([bytes], { type: mime });
}

// 8. UI Building & State Synchronization
const thumbnailGridEl = document.getElementById('thumbnail-grid');
const tagFilterEl = document.getElementById('tag-filter');
const poseCountBadgeEl = document.getElementById('pose-count-badge');
const promptTextEl = document.getElementById('prompt-text');
const copyPromptBtn = document.getElementById('copy-prompt');
const copyFeedbackEl = document.getElementById('copy-feedback');
const downloadPngBtn = document.getElementById('download-png');
const activePoseTitleEl = document.getElementById('active-pose-title');
const activeCameraInfoEl = document.getElementById('active-camera-info');

let copyFeedbackTimer = null;

function populateTagFilter() {
  if (!tagFilterEl) return;
  const tagSet = new Set();
  for (const id of getPoseIdsSorted()) {
    const entry = getCatalogEntryForPose(id);
    for (const t of entry.tags || []) {
      tagSet.add(t);
    }
  }
  const sortedTags = [
    ...CATEGORY_ORDER.filter((t) => tagSet.has(t)),
    ...Array.from(tagSet)
      .filter((t) => !CATEGORY_ORDER.includes(t))
      .sort((a, b) => a.localeCompare(b, 'ko')),
  ];

  tagFilterEl.innerHTML = '<option value="">전체 태그</option>';
  for (const tag of sortedTags) {
    const opt = document.createElement('option');
    opt.value = tag;
    opt.textContent = tag;
    tagFilterEl.appendChild(opt);
  }
  tagFilterEl.value = state.tagFilter;
}

function buildThumbnailCards() {
  if (!thumbnailGridEl) return;
  thumbnailGridEl.innerHTML = '';
  const ids = getPoseIdsSorted();

  for (const id of ids) {
    const entry = getCatalogEntryForPose(id);
    const btn = document.createElement('button');
    btn.type = 'button';
    btn.className = 'pose-card';
    btn.setAttribute('data-pose-id', id);
    btn.setAttribute('role', 'listitem');

    const thumbWrap = document.createElement('div');
    thumbWrap.className = 'pose-thumb-wrap';

    const canvas = document.createElement('canvas');
    canvas.className = 'pose-thumb-canvas';
    canvas.width = THUMB_WIDTH;
    canvas.height = THUMB_HEIGHT;
    thumbWrap.appendChild(canvas);

    const info = document.createElement('div');
    info.className = 'pose-card-info';

    const nameSpan = document.createElement('span');
    nameSpan.className = 'pose-card-name';
    nameSpan.textContent = entry.name || id;
    info.appendChild(nameSpan);

    if (Array.isArray(entry.tags) && entry.tags.length > 0) {
      const tagsRow = document.createElement('div');
      tagsRow.className = 'pose-card-tags';
      for (const tag of entry.tags.slice(0, 3)) {
        const chip = document.createElement('span');
        chip.className = 'pose-tag';
        chip.textContent = tag;
        tagsRow.appendChild(chip);
      }
      info.appendChild(tagsRow);
    }

    btn.appendChild(thumbWrap);
    btn.appendChild(info);

    btn.addEventListener('click', () => {
      selectPose(id);
    });

    thumbnailGridEl.appendChild(btn);
  }
}

function applyTagFilterToCards() {
  const ids = getPoseIdsSorted();
  let visibleCount = 0;
  for (const id of ids) {
    const card = document.querySelector(`[data-pose-id="${id}"]`);
    if (!card) continue;
    const entry = getCatalogEntryForPose(id);
    const matches =
      !state.tagFilter || (Array.isArray(entry.tags) && entry.tags.includes(state.tagFilter));
    card.hidden = !matches;
    if (matches) visibleCount++;
  }
  if (poseCountBadgeEl) {
    poseCountBadgeEl.textContent = `${visibleCount}개 포즈`;
  }
}

function updateUI() {
  // Thumbnail active state
  const cards = document.querySelectorAll('[data-pose-id]');
  for (const card of cards) {
    const id = card.getAttribute('data-pose-id');
    card.classList.toggle('active', id === state.poseId);
  }

  // Gender toggle state
  const genderBtns = document.querySelectorAll('[data-gender]');
  for (const btn of genderBtns) {
    const g = btn.getAttribute('data-gender');
    const isActive = g === state.gender;
    btn.classList.toggle('active', isActive);
    btn.setAttribute('aria-pressed', String(isActive));
  }

  // Angle preset state
  const angleBtns = document.querySelectorAll('[data-angle]');
  for (const btn of angleBtns) {
    const a = btn.getAttribute('data-angle');
    btn.classList.toggle('active', a === state.angle);
  }

  // HUD
  const entry = getCatalogEntryForPose(state.poseId);
  if (activePoseTitleEl) {
    activePoseTitleEl.textContent = entry.name || state.poseId;
  }
  if (activeCameraInfoEl) {
    const angleLabel = ANGLE_PRESETS[state.angle]?.label || state.angle;
    const genderLabel = state.gender === 'female' ? '여성' : '남성';
    activeCameraInfoEl.textContent = `${angleLabel} · ${genderLabel}`;
  }

  // Prompt text (#prompt-text must match promptText() verbatim)
  if (promptTextEl) {
    promptTextEl.textContent = getPromptText();
  }
}

// 9. Public / Hook Actions
function selectPose(id) {
  if (!posesMap.has(id)) {
    throw new Error(`알 수 없는 포즈 id입니다: ${id}`);
  }
  state.poseId = id;
  const rig = rigs[state.gender];
  const pose = posesMap.get(id);
  if (rig && pose) {
    setActiveRigVisibility(state.gender);
    applyPoseToRig(rig, pose);
  }
  updateUI();
  renderMain();
}

function setGender(gender) {
  if (gender !== 'female' && gender !== 'male') {
    throw new Error(`알 수 없는 성별입니다: ${gender}`);
  }
  const genderChanged = state.gender !== gender;
  state.gender = gender;

  setActiveRigVisibility(gender);
  const rig = rigs[gender];
  const pose = posesMap.get(state.poseId);
  if (rig && pose) {
    applyPoseToRig(rig, pose);
  }

  if (genderChanged) {
    renderAllThumbnailsForGender(gender);
  }

  updateUI();
  renderMain();
}

function setAngle(key) {
  if (!Object.hasOwn(ANGLE_PRESETS, key)) {
    throw new Error(`알 수 없는 앵글 프리셋입니다: ${key}`);
  }
  state.angle = key;
  controls.target.copy(CAMERA_TARGET);
  positionCameraForPreset(camera, controls.target, key);
  controls.update();
  state.angle = key;
  updateUI();
  renderMain();
}

// 10. Event Listeners
controls.addEventListener('change', () => {
  const nearest = findNearestPresetKey();
  if (state.angle !== nearest) {
    state.angle = nearest;
    updateUI();
  }
  renderMain();
});

for (const btn of document.querySelectorAll('[data-gender]')) {
  btn.addEventListener('click', () => {
    const g = btn.getAttribute('data-gender');
    if (g) setGender(g);
  });
}

for (const btn of document.querySelectorAll('[data-angle]')) {
  btn.addEventListener('click', () => {
    const key = btn.getAttribute('data-angle');
    if (key) setAngle(key);
  });
}

if (tagFilterEl) {
  tagFilterEl.addEventListener('change', () => {
    state.tagFilter = tagFilterEl.value;
    applyTagFilterToCards();
  });
}

if (downloadPngBtn) {
  downloadPngBtn.addEventListener('click', () => {
    const dataUrl = renderExportPngDataUrl();
    const blob = dataUrlToBlob(dataUrl);
    const blobUrl = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = blobUrl;
    a.download = `${state.poseId}_${state.gender}_${state.angle}.png`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    setTimeout(() => URL.revokeObjectURL(blobUrl), 10000);
  });
}

if (copyPromptBtn) {
  copyPromptBtn.addEventListener('click', async () => {
    const text = getPromptText();
    try {
      if (navigator.clipboard && typeof navigator.clipboard.writeText === 'function') {
        await navigator.clipboard.writeText(text);
      }
    } catch {
      // Ignore permission errors in headless/unfocused context
    }
    if (copyFeedbackEl) {
      copyFeedbackEl.hidden = false;
      if (copyFeedbackTimer) clearTimeout(copyFeedbackTimer);
      copyFeedbackTimer = setTimeout(() => {
        copyFeedbackEl.hidden = true;
      }, 2000);
    }
  });
}

window.addEventListener('resize', resizeViewport);

// 11. Initialization & Debug Hook
async function syncLivePosesIfAvailable() {
  try {
    const res = await fetch('/__pose_sync.json', { cache: 'no-store' });
    if (!res.ok) return;
    const payload = await res.json();
    if (payload && payload.poses && typeof payload.poses === 'object') {
      posesMap.clear();
      for (const [id, raw] of Object.entries(payload.poses)) {
        posesMap.set(id, sanitizePose(raw));
      }
    }
    if (payload && payload.catalog && Array.isArray(payload.catalog.poses)) {
      catalogMap.clear();
      for (const entry of payload.catalog.poses) {
        if (entry && entry.id) {
          catalogMap.set(entry.id, entry);
        }
      }
    }
  } catch {
    // Fallback to build-time import.meta.glob data
  }
}

async function initApp() {
  await syncLivePosesIfAvailable();

  const sortedIds = getPoseIdsSorted();
  if (!state.poseId || !posesMap.has(state.poseId)) {
    state.poseId = sortedIds[0] || '';
  }

  populateTagFilter();
  buildThumbnailCards();
  applyTagFilterToCards();

  const [femaleRig, maleRig] = await Promise.all([loadRig('female'), loadRig('male')]);
  rigs.female = femaleRig;
  rigs.male = maleRig;

  scene.add(femaleRig.root);
  scene.add(maleRig.root);

  // Apply initial pose to both rigs so both are initialized in valid pose state
  const initialPose = posesMap.get(state.poseId);
  if (initialPose) {
    applyPoseToRig(femaleRig, initialPose);
    applyPoseToRig(maleRig, initialPose);
  }

  setActiveRigVisibility(state.gender);
  resizeViewport();
  setAngle('front');

  // Render initial thumbnails (front preset, current gender)
  renderAllThumbnailsForGender(state.gender);
  updateUI();
  renderMain();
}

const readyPromise = initApp();

window.__poseApp = {
  ready: readyPromise,
  poseIds() {
    return getPoseIdsSorted();
  },
  selectPose(id) {
    selectPose(id);
  },
  setGender(gender) {
    setGender(gender);
  },
  setAngle(key) {
    setAngle(key);
  },
  getState() {
    return {
      poseId: state.poseId,
      gender: state.gender,
      angle: state.angle,
    };
  },
  cameraAngles() {
    return computeCameraAngles();
  },
  jointPositions() {
    return computeJointPositions(state.gender);
  },
  promptText() {
    return getPromptText();
  },
};
