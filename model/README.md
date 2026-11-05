# Female / male mannequin bases — QA v2 revision

`female.glb` is the reproducible female base. This revision changes the chest shell only; shoulder, waist, pelvis, abdomen and limbs retain the preceding geometry. Original canonical vertices **0–4105**, UVs and joint/weight attributes remain in order. No commit was made.

## Source and coordinates

`male.glb`: glTF 2.0; 63 nodes, two triangle meshes/primitives. Body: 2,858 attribute vertices / 1,456 triangles. Joints: 1,248 / 632. Total **4,106 vertices / 2,088 triangles**, including shading/UV duplicates. One skin, 55 joints and inverse bind matrices; no animations.

Meters, Y-up, front +Z. Male height **1.89998439 m**, female **1.75748554 m** (7.5% shorter). Origin is between feet on the floor within float tolerance. Male bbox min `[-0.68752176, -3.07e-8, -0.17833138]`, max `[0.68752325, 1.89998436, 0.16584653]`. Source scene contains axis rotations and a skin hierarchy; accessor positions define the canonical rest shape.

Unchanged materials: gray Body `(0.8,0.8,0.8)`, roughness 0.821115; dark Joints `(0.0338957,0.0338957,0.0338957)`, roughness 0.992421. Both double-sided, nonmetallic and untextured.

## Reproduce

Python 3 + NumPy, with the existing read-only QA utilities for measurements. No GUI, Blender or network is required for geometry generation. From the repository root:

```sh
PYTHONDONTWRITEBYTECODE=1 /tmp/pose-qa-venv/bin/python model/tools/build_female.py
PYTHONDONTWRITEBYTECODE=1 /tmp/pose-qa-venv/bin/python model/tools/qa_bust_summary.py
PYTHONDONTWRITEBYTECODE=1 /tmp/pose-qa-venv/bin/python model/tools/render_previews.py
PYTHONDONTWRITEBYTECODE=1 /tmp/pose-qa-venv/bin/python model/tools/verify.py
NODE_PATH=/private/tmp/pose-model-validator/node_modules node model/tools/validate_glb.cjs
PYTHONDONTWRITEBYTECODE=1 /tmp/pose-qa-venv/bin/python -m pytest tests -q -p no:cacheprovider
```

`build_female.py` runs the fixed-topology base deformation, saves `validation/female_before_breast_refinement.glb`, refines the chest and writes generation diagnostics. `qa_bust_summary.py` reads `tests/bust_eval.py` / `qa_metrics.py` without modifying them and writes the authoritative **QA v2** measurements to `validation/qa_bust_v2.json`. Geometry generation is deterministic. Current GLB SHA-256: `8c02e2a8dbc501419998e710d101204656447121a7f6d183ce473bb527ffd768`.

## Construction and correspondence

Method: **local subdivision of the existing connected chest shell**, chosen to avoid a separate breast patch and weld seam. Connectivity on source-position-welded geometry identifies the chest, excluding abdomen and pelvis. Its 116 triangles become 11,600 triangles (10 subdivisions per edge). The whole connected shell is refined, including side/back faces, to avoid T-junctions. Other components' triangles are unchanged.

Final GLB: one mesh, two material primitives sharing a canonical vertex pool. A reader must deduplicate shared accessors when counting vertices.

| Canonical indices, inclusive | Source correspondence |
|---|---|
| 0–2857 | Male Body local 0–2857 |
| 2858–4105 | Male Joints local 0–1247, plus 2858 |
| **4106–10846** | **6,741 appended chest vertices** |

Total **10,847 vertices / 13,572 triangles**, unchanged from the preceding refined female. Original chest vertices can change position/normal. Every original non-chest position remains unchanged. Original UV / JOINTS_0 / WEIGHTS_0 values compare exactly. New attributes are barycentrically interpolated; joint influences are accumulated by joint ID, strongest four retained and renormalized. Final normals are recalculated from actual final triangles, with source hard-edge groups retained on back/top and smooth area-weighted normals on the rounded front.

`validation/chest_vertex_mapping.json` contains each appended index, three original canonical parent indices and barycentric weights. `triangle_source` maps every final triangle back to the original male triangle domain (Body 0–1455, Joints 1456–2087). Corner indices are reused and original UV/hard-edge duplicate positions stay coincident.

## Changes for QA v2

- Removed the separate central Gaussian ridge. Two asymmetric Gaussian lobes now overlap through their long inner tails, making **one broad U-shaped hollow**, rather than a central peak with two side grooves. Centers remain x ±75 mm; inner / outer widths are **70 / 21 mm**.
- Displacement amplitude is **61.8 mm**. The field center is y **1.295 m**. Upper support is **180 mm** with a softened concave power profile: `q'=1.1q²/(q+0.1)`, then `(1−q')^3.7`. The low-amplitude upper tail fades into the existing upper chest. Lower support is **95 mm**, with `1−3q⁴+2q⁶`, giving a fuller lower contour and smooth return at the fold.
- A small **8 mm** localized correction centered at y 1.268 m smooths the inherited coarse front-wall ridge that otherwise pulled the measured apex downward. A **9 mm** local fold return centered at y 1.185 m (17 mm vertical width) makes the IMF clearer without pulling the chest through the abdomen. These terms operate on the chest shell only.
- Lower ribcage depth is supported by a **7.5 mm posterior chest-shell return** centered at y 1.19 m (50 mm width). This adjusts underbust girth while keeping abdomen, waist and pelvis unchanged. It is explicitly part of the chest remodeling, not a change to hip/waist coefficients.
- The original anterior bottom-rim return is softened by a conservative **0.5 mm** local correction. Larger retreats caused abdomen contact or changed the inferred QA wall enough to reintroduce false low-volume tails; those trials were discarded. **The source's segmented bottom rim is still partly visible.** It is not claimed to be a seamless anatomical torso.
- Shoulder / waist / hip base coefficients, upper-hip affine plateau, limb proportions and overall height are unchanged. No QA thresholds were changed.

## Final QA v2 measurements

These use the requested **QA measurement method**, not the generator's known pre-displacement wall. Girths are horizontal convex-hull perimeters. Volume and projection use the QA 2 mm heightfield and extrapolated quadratic chest wall.

| Metric | Previous QA v2 report | Revised |
|---|---:|---:|
| Bust − underbust | 16.2 cm | **15.055 cm** |
| One breast volume | ~453 cm³ | **449.03 / 448.18 cm³** |
| Wall-relative projection | ~64 mm | **60.81 / 60.43 mm** |
| Upper pole volume fraction | ~0.518 | **0.45246 / 0.45114** |
| Apex relative height, bottom=0 / top=1 | ~0.505 | **0.45263** |
| Lower contour convexity | ~0.012 | **0.1683 / 0.1686** |
| Upper contour convexity | ~0.051 | **−0.0366 / −0.0374** |
| IMF angle | ~41.6° | **51.16 / 51.04°** |
| Upper return angle | ~38.8° | **25.82 / 25.67°** |
| Sternum ridge | ~12.8 mm | **0.336 mm** |
| Midline curvature | ~78 /m | **9.72 /m** |
| Maximum dihedral | ~50° | **45.80°** |
| Vertex deviation | ~4.5 mm | **4.90 mm** |

The apex is below half-height. Its 0.4526 relative height is about 0.003 above the preferred 0.42–0.45 interval, within one 2 mm grid step; the strict `<0.5` requirement passes. The upper-pole fraction and volume lie inside the requested preferred ranges.

Bust **103.151 cm** at y **1.288177 m**; underbust **88.096 cm** at y **1.192177 m**. The generator's `breast_metrics.json` uses a different known-wall integration and a fixed underbust height; its volume (~536 cm³) is not interchangeable with QA's annulus-fit / bounded-disc estimate. QA v2 values above are the requested acceptance measurements. This difference is a remaining measurement-method uncertainty, not a bra-fit guarantee.

New chest-partner faces versus male: **upper arm 0, abdomen 0, waist band 0**. Abdomen poke is **−0.348 mm**, so the abdomen is behind the chest surface at the worst sampled location. Existing source contacts remain. The independent source-face-pair diagnostic records **6 changed chest–abdomen pairings on already-contacted abdomen faces**, and 14 contact triangles with any nonzero breast displacement; this is a different metric from QA v2's new opposite-partner faces. The asset is not claimed to be intersection-free. Shoulder/hip breadth ratio is **0.99029** using QA v2's 0.44H–0.56H zone; WHR is **0.74094**, both unchanged and passing. The older pelvis-ring-only width ratio is a different definition and is not used here.

## Test results

Latest full requested command: **103 passed, 4 skipped, 1 failed** (`validation/pytest_v2_output.txt`). **All 15 `test_08_bust` tests pass.** The single failure is `test_06_proportions.py::test_waist_to_bust_girth`, explicitly permitted to remain by the current instruction because that old criterion is being retired. The four skips are coarse-chest checks superseded by the refined-surface tests. Tests and scripts were read/executed without edits.

Official glTF validator: **0 errors, 1 warning, 2 infos**. Warning: retained JOINTS/WEIGHTS on an intentionally unskinned static base. Infos: unused UVs on untextured primitives. Full reports remain under `model/validation/`. QA topology, attribute, finite-value, seam, symmetry and non-chest preservation checks pass.

`previews/female_front.png`, `female_side.png`, `female_three_quarter.png`, `female_chest_side.png` use **geometric face normals**. They were rerendered and opened for visual inspection: the W-shaped vertical double groove is gone, the lower pole is fuller, and the lower fold is clearer. Facet bands remain visible under deliberately flat face shading. The small inherited bottom rim remains as noted above.

## Remaining limitations and attribution

This is an unskinned base. Existing source connector/shell overlaps and the recessed waist connector design remain. The current rigid lowered-arm proxy found 0 contacts on expanded breast triangles at 30°, 40° and 45° inward arm rotation, and 0 new pairs due to breast volume. Inherited chest-wall/arm source pairs are 52 / 56 / 64 and actual fitted-skeleton poses still require rigger validation. No new rig or pose changes were made.

Source author: **RD3D Game Design**. Source: [UE Mannequin Demake](https://sketchfab.com/3d-models/ue-mannequin-demake-929c983369ec435196a215d29dd6d907). License: **CC BY 4.0**, as recorded in `male.glb`. Female modifications: feminine proportions, 7.5% height reduction, chest subdivision and breast/ribcage shaping. Original attribution/license metadata is preserved.
