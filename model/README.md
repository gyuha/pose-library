# Male / female mannequin bases

`female.glb` is a reproducible, static feminine base derived from `male.glb` by a symmetric continuous position deformation. No vertices, triangles or vertex indices were added, removed or reordered. UVs, original joint indices and weights, materials, and source attribution remain in the file. The source GLB is unchanged.

## Source analysis

- glTF 2.0 binary, 63 nodes, two triangle meshes / two primitives.
- `Male_v2_Body`: 2,858 attribute vertices, 1,456 triangles.
- `Male_v2_Joints`: 1,248 attribute vertices, 632 triangles.
- Total: **4,106 vertices, 2,088 triangles** (includes duplicated vertices at shading/UV seams; not welded counts).
- One skin, 55 joints, JOINTS_0 / WEIGHTS_0 attributes and inverse bind matrices; no animations.
- Meters (glTF convention; human-scale coordinates), Y-up, front +Z. Vertex coordinates have height 1.89998436 m. Source scene contains cancelling axis rotations and a skin hierarchy; source accessor coordinates provide the canonical rest shape.
- Source bbox: min `[-0.68752176, -0.0000000307, -0.17833138]`, max `[0.68752325, 1.89998436, 0.16584653]` m. Origin is centered between feet at the floor, within floating point tolerance. Feet extend in +Z.
- Materials: Body, gray `(0.8,0.8,0.8)`, roughness 0.821115; Joints, dark gray `(0.0338957,0.0338957,0.0338957)`, roughness 0.992421. Both nonmetallic, double-sided; no textures.

## Generation and rendering

Tools: Python 3 + NumPy, a deterministic NumPy orthographic triangle rasterizer (z-buffer and geometric face normals), and official Node glTF validator. Blender's GUI/headless executable crashed on the original machine; Blender is not required. The QA NumPy environment is used for the revised build.

From the repository root:

```sh
PYTHONDONTWRITEBYTECODE=1 /tmp/pose-qa-venv/bin/python model/tools/make_female.py
PYTHONDONTWRITEBYTECODE=1 /tmp/pose-qa-venv/bin/python model/tools/render_previews.py
PYTHONDONTWRITEBYTECODE=1 /tmp/pose-qa-venv/bin/python model/tools/verify.py
PYTHONDONTWRITEBYTECODE=1 /tmp/pose-qa-venv/bin/python model/tools/qa_summary.py
NODE_PATH=/private/tmp/pose-model-validator/node_modules node model/tools/validate_glb.cjs
PYTHONDONTWRITEBYTECODE=1 /tmp/pose-qa-venv/bin/python -m pytest tests -q -p no:cacheprovider
```

`make_female.py` uses `deformation.py`. Components are computed from source-position-welded triangle connectivity, then classified by their source centroids; this does not import QA code. Only the chest component receives the breast field. Abdomen and pelvis receive none. Joint attributes, UVs and index buffers are untouched. `qa_summary.py` reads QA metrics to write a reviewable summary under `model/validation/`; generation is independent of tests.

Revised coefficients compared with the first female:

- Shoulder reduction 0.22 → 0.07; waist reduction 0.32 → 0.12; broad hip term 0.38 → 0.27. These are Gaussian field amplitudes, not final measured widths.
- Arm inward translation 37 mm → **0**. Arms and their connectors share x scale 0.94, with unchanged depth, avoiding articulation drift.
- Breast amplitude 85 mm → **28 mm**; lateral Gaussian width 71 → **150 mm**, vertical width 85 → **190 mm**. A broad lateral falloff and upper/lower chest-only fade prevent isolated peaks and interference at the shell ends.
- Removed the localized 48 mm posterior gluteal bump and 18 mm thigh offset. Pelvis, hip joints and upper thighs share the same affine plateau (x ×1.23, z ×1.10 in source y 0.78–0.99 m), preventing differential motion at hip contacts.
- Neck taper fades in above source y 1.62 m; head/neck x/z narrowing is 6% / up to 10%.
- Height remains ×0.925 around the floor origin.

Normals are recalculated by accumulating final triangle cross products, preserving authored hard-edge groups identified by source position and source normal. No inverse-Jacobian normal transformation remains. Preview shading uses **geometric face normals**, not stored NORMAL attributes. No remeshing, subdivision or manual editing occurs.

Female has two identity mesh nodes, Y-up, the same origin and materials. Its male skin/skeleton is removed: this is an **unskinned base for the rigger**. Original JOINTS_0 / WEIGHTS_0 data and the unused inverse-bind accessor remain for reference. The rigger must fit female joint positions and bind matrices.

## Validation after revision

**72 passed, 0 failed** using the pytest command above. Tests and scripts were read/executed without edits. Full latest generation/validator/intersection reports and QA metric summary live in `model/validation/`.

| Metric | Previous female (QA report) | Revised female |
|---|---:|---:|
| Shoulder width | 0.325 m | 0.403493 m |
| Hip width (pelvis/joints) | 0.381 m | 0.333021 m |
| Shoulder / hip width | 0.85 | **1.211615** |
| Waist / hip girth | 0.55 | **0.740940** |
| Waist / bust girth | 0.53 | **0.663497** |
| Waist girth | ~0.55 m | 0.658474 m |
| Hip girth | ~1.00 m | 0.888702 m |
| Chest central groove | ~58 mm | **0 mm** |
| New strict intersection pairs | 67 | **7** |
| New Body–Body intersections | ≥32 | **0** |

The 7 remaining new pairs are chest–shoulder connector (3 per side) and left thigh–knee connector (1). There are **0** new chest–abdomen, chest–upper-arm, pelvis–thigh, pelvis–waist-band and abdomen–waist-band pairs. Absolute intersections are male 1,369 / female 1,373, with 3 original pairs resolved. This diagnostic excludes shared-edge/end-point and coplanar contacts; the source has intentional intersecting components.

Both models retain **4,106 attribute vertices / 2,088 triangles**, exact indices, UVs, joints and weights. Female height is **1.75748554 m**, 7.5% below male **1.89998439 m**. No nonfinite values, degenerate triangles or face-normal reversals. All QA symmetry, local smoothness, stored-normal, seam and proportion checks pass.

Official gltf-validator: female **0 errors, 2 warnings, 3 infos**. Warnings concern retained JOINTS/WEIGHTS on the unskinned static meshes; infos concern unused UVs and inverse-bind accessor. Source male also has 0 errors / 2 warnings / 3 infos.

`previews/{male,female}_{front,side,three_quarter}.png` were rerendered with geometric face shading. The three female images were opened and inspected: the lower chest dent and pointed peaks are gone, the waist band is visible, and the pelvis is less inflated. Shape remains faceted with a restrained bust, rather than a smooth anatomical breast surface. Numerical targets were met without reverting to male waist/hip proportions.

### Waist-band constraint that remains unresolved

The requested strict rule “band outer radius always exceeds the pelvis top ring” is **not established by this revision**. The source band is an internal connector, not an external belt: its oblique ring axis is approximately `(0, 0.91477, 0.40398)`. At the shared lower interface, revised band x span is about **0.209 m**, while the pelvis upper ring is about **0.268 m**. Their original spans are also nested (about 0.220 / 0.282 m). A simple top-ring recess to enforce the requested ordering created a visible dent, 29 new band/pelvis intersections and 8.5 mm seam-distance growth; it was discarded. The final version retains the source's recessed connector construction, passes all 28 seam checks and has zero new band/pelvis crossings. This is a remaining design constraint, not a claim that the QA thresholds are wrong.

## Limits and attribution

This retains the source's faceted, segmented low-poly mannequin aesthetic. The very sparse chest and head topology limits round breasts, subtle facial detail and muscle smoothing; the face is featureless and the chest profile remains angular. Topology preservation precludes adding anatomical detail. The result is a stylized female base, not a realistic anatomical scan or clean continuous skin. Connector overlaps remain as quantified above. The strict external-belt radius rule remains unresolved as described above.

Source author: **RD3D Game Design**. Source: [UE Mannequin Demake](https://sketchfab.com/3d-models/ue-mannequin-demake-929c983369ec435196a215d29dd6d907). License: **CC BY 4.0**, as recorded in `male.glb` metadata. Female modification: procedural feminine proportions and 7.5% height reduction. Original author/license metadata is preserved in `female.glb`.
