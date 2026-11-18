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
const THUMB_WIDTH = 240;
const THUMB_HEIGHT = 320;
const CAMERA_FOV = 26;
// Fallback framing used only when no rig/bounding box is available yet.
const CAMERA_DISTANCE = 5.3;
const CAMERA_TARGET = new THREE.Vector3(0, 0.96, 0);
// Fraction of each image edge kept empty around the posed figure.
const FRAME_MARGIN = 0.05;
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

function syncLightsToCamera(refCam = camera, target = controls.target) {
  refCam.updateMatrixWorld(true);
  const right = new THREE.Vector3();
  const up = new THREE.Vector3();
  const back = new THREE.Vector3();
  refCam.matrixWorld.extractBasis(right, up, back);

  keyLight.position
    .copy(target)
    .addScaledVector(right, -2.2)
    .addScaledVector(up, 3.4)
    .addScaledVector(back, 4.6);

  fillLight.position
    .copy(target)
    .addScaledVector(right, 3.0)
    .addScaledVector(up, 1.2)
    .addScaledVector(back, 3.2);
}

// Auto-framing helpers: only the orbit target and distance change; the preset
// yaw/pitch handed to cameraAngles() stays exact.
const WORLD_UP = new THREE.Vector3(0, 1, 0);
const _frameCenter = new THREE.Vector3();
const _frameForward = new THREE.Vector3();
const _frameRight = new THREE.Vector3();
const _frameUp = new THREE.Vector3();
const _frameCorner = new THREE.Vector3();
const _frameOffset = new THREE.Vector3();

// Unit vector from the orbit target towards the camera for a preset.
function presetCameraDirection(presetKey, out = new THREE.Vector3()) {
  const preset = ANGLE_PRESETS[presetKey];
  const yawRad = (preset.yawDeg * Math.PI) / 180;
  const pitchRad = (preset.pitchDeg * Math.PI) / 180;
  const horiz = Math.cos(pitchRad);
  return out.set(-horiz * Math.sin(yawRad), Math.sin(pitchRad), horiz * Math.cos(yawRad));
}

// Points `cam` at the centre of `box` from the preset yaw/pitch and picks the
// smallest distance that keeps all eight box corners inside the frame with
// FRAME_MARGIN on every edge. Returns the orbit target (a new vector).
function fitCameraToBox(cam, presetKey, box, aspect) {
  const hasBox = box && !box.isEmpty();
  const center = hasBox ? box.getCenter(_frameCenter) : _frameCenter.copy(CAMERA_TARGET);
  const forward = presetCameraDirection(presetKey, _frameForward);
  const right = _frameRight.crossVectors(WORLD_UP, forward).normalize();
  const up = _frameUp.crossVectors(forward, right).normalize();

  const tanV = Math.tan((cam.fov * Math.PI) / 360);
  const tanH = tanV * Math.max(aspect, 1e-6);
  const usable = 1 - 2 * FRAME_MARGIN;

  let distance = 0;
  if (hasBox && tanH > 0 && tanV > 0) {
    for (let i = 0; i < 8; i++) {
      _frameCorner.set(
        i & 1 ? box.max.x : box.min.x,
        i & 2 ? box.max.y : box.min.y,
        i & 4 ? box.max.z : box.min.z
      );
      _frameOffset.subVectors(_frameCorner, center);
      const along = _frameOffset.dot(forward);
      distance = Math.max(
        distance,
        along + Math.abs(_frameOffset.dot(right)) / (tanH * usable),
        along + Math.abs(_frameOffset.dot(up)) / (tanV * usable)
      );
    }
  }
  if (!(distance > 0)) distance = CAMERA_DISTANCE;

  cam.position.copy(center).addScaledVector(forward, distance);
  cam.up.copy(WORLD_UP);
  cam.lookAt(center);
  cam.updateProjectionMatrix();
  cam.updateMatrixWorld(true);
  return center.clone();
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
  if (rigs[state.gender]) {
    frameMainCamera(state.angle);
  }
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
  rig.currentPoseId = pose?.meta?.id || null;
}

// Bounding box of the *posed* skinned vertices (not the rest pose). Cached per
// rig/pose: the box only depends on the applied pose of that gender.
function getPosedBoundingBox(rig, poseId) {
  if (!rig) return null;
  if (!rig.boxCache) rig.boxCache = new Map();
  const cached = rig.boxCache.get(poseId);
  if (cached) return cached;

  const box = new THREE.Box3();
  for (const sm of rig.skinnedMeshes) {
    // precise=true evaluates getVertexPosition → applies bone/skin transforms.
    box.expandByObject(sm, true);
  }
  if (box.isEmpty()) return null;
  // Only cache boxes measured while this exact pose was applied.
  if (rig.currentPoseId === poseId) rig.boxCache.set(poseId, box);
  return box;
}

// Frame the on-screen camera for the current pose/angle.
function frameMainCamera(angleKey = state.angle) {
  const rig = rigs[state.gender];
  const box = rig ? getPosedBoundingBox(rig, state.poseId) : null;
  const aspect = camera.aspect || 3 / 4;
  const target = fitCameraToBox(camera, angleKey, box, aspect);
  controls.target.copy(target);
  controls.update();
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
function getPromptText(language = 'ko') {
  const pose = posesMap.get(state.poseId);
  if (!pose) return '';
  const catalogEntry = getCatalogEntryForPose(state.poseId);
  if (language === 'en') {
    const angle = { front: 'front view', side: 'right-side view', three_quarter: 'right three-quarter view', high: 'high-angle view', low: 'low-angle view' }[state.angle];
    const description = catalogEntry.descriptionEn || catalogEntry.description;
    return `Subject: ${state.gender === 'female' ? 'female' : 'male'} full-body character\nView: ${angle}\nPose: ${description}`;
  }
  return buildPosePrompt({
    pose,
    catalogEntry,
    gender: state.gender,
    angle: state.angle,
  });
}

// 7. Offscreen Thumbnail Rendering (thumbnails only)
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

  const aspect = THUMB_WIDTH / THUMB_HEIGHT;
  offscreenRenderer.setSize(THUMB_WIDTH, THUMB_HEIGHT, false);
  offscreenCamera.fov = CAMERA_FOV;
  offscreenCamera.aspect = aspect;
  const thumbBox = getPosedBoundingBox(rig, poseId);
  const thumbTarget = fitCameraToBox(offscreenCamera, 'front', thumbBox, aspect);
  syncLightsToCamera(offscreenCamera, thumbTarget);
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
  frameMainCamera(state.angle);
  renderMain();
}

// Capture the on-screen main canvas exactly as displayed. A fresh render
// right before capture guards against an empty buffer.
function renderMainCanvasPngDataUrl() {
  renderMain();
  return mainRenderer.domElement.toDataURL('image/png');
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
const tagComboEl = document.getElementById('tag-combo');
const tagListboxEl = document.getElementById('tag-filter-listbox');
const poseCountBadgeEl = document.getElementById('pose-count-badge');
const promptTextEl = document.getElementById('prompt-text');
const promptTextEnEl = document.getElementById('prompt-text-en');
const copyPromptKoBtn = document.getElementById('copy-prompt-ko');
const copyPromptEnBtn = document.getElementById('copy-prompt-en');
const copyFeedbackEl = document.getElementById('copy-feedback');
const downloadPngBtn = document.getElementById('download-png');
const activePoseTitleEl = document.getElementById('active-pose-title');
const activeCameraInfoEl = document.getElementById('active-camera-info');

let copyFeedbackTimer = null;

// Searchable tag combobox: text input + dropdown list with choseong search.
// `state.tagFilter` semantics are unchanged: '' means "no filter".
let allTags = [];
let filteredTagEntries = []; // [{ value, label }] currently shown; always starts with '' entry
let activeTagOptionIndex = -1;

const CHOSEONG = 'ㄱㄲㄴㄷㄸㄹㅁㅂㅃㅅㅆㅇㅈㅉㅊㅋㅌㅍㅎ';

function toChoseong(str) {
  let out = '';
  for (const ch of str) {
    const code = ch.charCodeAt(0);
    if (code >= 0xac00 && code <= 0xd7a3) {
      out += CHOSEONG[Math.floor((code - 0xac00) / 588)];
    } else {
      out += ch;
    }
  }
  return out;
}

function tagMatchesQuery(tag, query) {
  const q = (query || '').trim();
  if (!q) return true;
  if (tag.includes(q)) return true;
  return toChoseong(tag).includes(q);
}

function getFilteredTagEntries(query) {
  const entries = [{ value: '', label: '전체 태그' }];
  for (const tag of allTags) {
    if (tagMatchesQuery(tag, query)) entries.push({ value: tag, label: tag });
  }
  return entries;
}

function selectTagFilter(value) {
  state.tagFilter = value;
  if (tagFilterEl) tagFilterEl.value = value;
  applyTagFilterToCards();
}

function updateTagActiveDescendant() {
  if (!tagFilterEl) return;
  if (
    !tagListboxEl ||
    tagListboxEl.hidden ||
    activeTagOptionIndex < 0 ||
    activeTagOptionIndex >= filteredTagEntries.length
  ) {
    tagFilterEl.removeAttribute('aria-activedescendant');
    return;
  }
  tagFilterEl.setAttribute('aria-activedescendant', `tag-filter-option-${activeTagOptionIndex}`);
}

function renderTagListbox() {
  if (!tagListboxEl) return;
  tagListboxEl.innerHTML = '';
  filteredTagEntries.forEach((entry, i) => {
    const li = document.createElement('li');
    li.id = `tag-filter-option-${i}`;
    li.className = 'tag-filter-option';
    li.setAttribute('role', 'option');
    li.setAttribute('data-tag-value', entry.value);
    const isSelected = state.tagFilter === entry.value;
    li.setAttribute('aria-selected', String(isSelected));
    if (isSelected) li.classList.add('selected');
    if (i === activeTagOptionIndex) li.classList.add('active');
    li.textContent = entry.label;
    // mousedown fires before input blur; preventDefault keeps focus so the
    // click always lands even though blur would otherwise close the list.
    li.addEventListener('mousedown', (e) => {
      e.preventDefault();
      selectTagFilter(entry.value);
      closeTagListbox();
      tagFilterEl?.focus();
    });
    tagListboxEl.appendChild(li);
  });
  updateTagActiveDescendant();
  const activeEl = tagListboxEl.children[activeTagOptionIndex];
  if (activeEl && typeof activeEl.scrollIntoView === 'function') {
    activeEl.scrollIntoView({ block: 'nearest' });
  }
}

function refreshTagListbox(query) {
  filteredTagEntries = getFilteredTagEntries(query);
  activeTagOptionIndex = filteredTagEntries.findIndex((e) => e.value === state.tagFilter);
  if (activeTagOptionIndex < 0) activeTagOptionIndex = filteredTagEntries.length ? 0 : -1;
  renderTagListbox();
}

function openTagListbox() {
  if (!tagListboxEl || !tagFilterEl) return;
  if (!tagListboxEl.hidden) return;
  tagListboxEl.hidden = false;
  tagFilterEl.setAttribute('aria-expanded', 'true');
  refreshTagListbox(tagFilterEl.value);
}

function closeTagListbox(restoreInput = false) {
  if (restoreInput && tagFilterEl) tagFilterEl.value = state.tagFilter;
  activeTagOptionIndex = -1;
  if (tagListboxEl) tagListboxEl.hidden = true;
  if (tagFilterEl) {
    tagFilterEl.setAttribute('aria-expanded', 'false');
    tagFilterEl.removeAttribute('aria-activedescendant');
  }
}

function moveTagActiveOption(delta) {
  if (!filteredTagEntries.length) return;
  const n = filteredTagEntries.length;
  activeTagOptionIndex = ((activeTagOptionIndex + delta) % n + n) % n;
  renderTagListbox();
}

function populateTagFilter() {
  const tagSet = new Set();
  for (const id of getPoseIdsSorted()) {
    const entry = getCatalogEntryForPose(id);
    for (const t of entry.tags || []) {
      tagSet.add(t);
    }
  }
  allTags = [
    ...CATEGORY_ORDER.filter((t) => tagSet.has(t)),
    ...Array.from(tagSet)
      .filter((t) => !CATEGORY_ORDER.includes(t))
      .sort((a, b) => a.localeCompare(b, 'ko')),
  ];

  if (!tagFilterEl) return;
  tagFilterEl.value = state.tagFilter;
  filteredTagEntries = getFilteredTagEntries('');
  activeTagOptionIndex = -1;
  renderTagListbox();
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
  if (promptTextEnEl) promptTextEnEl.textContent = getPromptText('en');
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
  frameMainCamera(state.angle);
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

  frameMainCamera(state.angle);
  updateUI();
  renderMain();
}

function setAngle(key) {
  if (!Object.hasOwn(ANGLE_PRESETS, key)) {
    throw new Error(`알 수 없는 앵글 프리셋입니다: ${key}`);
  }
  state.angle = key;
  frameMainCamera(key);
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
  tagFilterEl.addEventListener('input', () => {
    openTagListbox();
    refreshTagListbox(tagFilterEl.value);
  });

  tagFilterEl.addEventListener('focus', () => {
    openTagListbox();
  });

  tagFilterEl.addEventListener('blur', () => {
    // Option mousedown uses preventDefault, so a real blur means focus left
    // the combobox: close and revert uncommitted text to the selection.
    closeTagListbox(true);
  });

  tagFilterEl.addEventListener('keydown', (e) => {
    if (e.key === 'ArrowDown' || e.key === 'ArrowUp') {
      e.preventDefault();
      openTagListbox();
      moveTagActiveOption(e.key === 'ArrowDown' ? 1 : -1);
    } else if (e.key === 'Enter') {
      if (tagListboxEl && !tagListboxEl.hidden && filteredTagEntries[activeTagOptionIndex]) {
        e.preventDefault();
        selectTagFilter(filteredTagEntries[activeTagOptionIndex].value);
        closeTagListbox();
      }
    } else if (e.key === 'Escape') {
      if (tagListboxEl && !tagListboxEl.hidden) {
        e.preventDefault();
        closeTagListbox(true);
      }
    }
  });
}

document.addEventListener('pointerdown', (e) => {
  if (
    tagComboEl &&
    tagListboxEl &&
    !tagListboxEl.hidden &&
    !tagComboEl.contains(e.target)
  ) {
    closeTagListbox(true);
  }
});

if (downloadPngBtn) {
  downloadPngBtn.addEventListener('click', () => {
    const dataUrl = renderMainCanvasPngDataUrl();
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

for (const [button, language] of [[copyPromptKoBtn, 'ko'], [copyPromptEnBtn, 'en']]) {
  if (button) button.addEventListener('click', async () => {
    const text = getPromptText(language);
    let copied = false;
    try {
      if (navigator.clipboard && typeof navigator.clipboard.writeText === 'function') {
        await navigator.clipboard.writeText(text);
        copied = true;
      } else {
        const field = document.createElement('textarea');
        field.value = text;
        field.setAttribute('readonly', '');
        field.style.position = 'fixed';
        field.style.opacity = '0';
        document.body.appendChild(field);
        field.select();
        copied = document.execCommand('copy');
        field.remove();
      }
    } catch { copied = false; }
    if (copyFeedbackEl && copied) {
      copyFeedbackEl.textContent = language === 'ko' ? '한글 복사됨' : 'English copied';
      copyFeedbackEl.hidden = false;
      if (copyFeedbackTimer) clearTimeout(copyFeedbackTimer);
      copyFeedbackTimer = setTimeout(() => {
        copyFeedbackEl.hidden = true;
      }, 2000);
    } else if (copyFeedbackEl) {
      copyFeedbackEl.textContent = '복사에 실패했습니다. 텍스트를 직접 선택해 복사해 주세요.';
      copyFeedbackEl.hidden = false;
    }
  });
}

window.addEventListener('resize', resizeViewport);

// 11. Initialization & Debug Hook
async function initApp() {
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
