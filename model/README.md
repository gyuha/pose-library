# Female / male mannequin bases — v4 faceted chest revision

`female.glb` is the reproducible female base. Only the chest shell changes: a **low-poly faceted remesh (594 triangles)** whose edge flow follows the breast form. Shoulder, waist, pelvis, abdomen, limbs and height are unchanged. Original canonical vertices **0–4105**, their order, UVs and joint/weight attributes are unchanged. No commit was made.

v4 changes relative to v3:
- **Apex.** The 16-spoke apex pole is replaced by a flat 8-sided cap, an 8-sided loop and 16-sided rings, and the profiles are rounder.
- **Size and girth.** The breast is a little smaller (true bust − underbust 15.8 cm instead of 18.4 cm).
- **Bottom ledge.** The plate's bottom ledge is rounded back over its last 3 cm (centre overhang 3.5 mm instead of 7.8 mm).
- **Axis yaw.** The breast axis yaw goes from 10° to 12°.
- **Symmetry.** Quad splits are now mirrored exactly.

## Source and coordinates

`male.glb`: glTF 2.0; 63 nodes, two triangle meshes/primitives. Body: 2,858 attribute vertices / 1,456 triangles. Joints: 1,248 / 632. Total **4,106 vertices / 2,088 triangles**, including shading/UV duplicates. One skin, 55 joints and inverse bind matrices; no animations.

Meters, Y-up, front +Z. Male height **1.89998439 m**, female **1.75748551 m** (7.5% shorter). Origin is between feet on the floor within float tolerance. Male bbox min `[-0.68752176, -3.07e-8, -0.17833138]`, max `[0.68752325, 1.89998436, 0.16584653]`. Source scene contains axis rotations and a skin hierarchy; accessor positions define the canonical rest shape.

Unchanged materials: gray Body `(0.8,0.8,0.8)`, roughness 0.821115; dark Joints `(0.0338957,0.0338957,0.0338957)`, roughness 0.992421. Both double-sided, nonmetallic and untextured.

## Reproduce

Python 3 + NumPy, with the existing read-only QA utilities for measurements. No GUI, Blender or network is required for geometry generation. From the repository root:

```sh
PYTHONDONTWRITEBYTECODE=1 /tmp/pose-qa-venv/bin/python model/tools/build_female.py
PYTHONDONTWRITEBYTECODE=1 /tmp/pose-qa-venv/bin/python model/tools/qa_bust_summary.py
PYTHONDONTWRITEBYTECODE=1 /tmp/pose-qa-venv/bin/python model/tools/render_previews.py
PYTHONDONTWRITEBYTECODE=1 /tmp/pose-qa-venv/bin/python model/tools/verify.py
PYTHONDONTWRITEBYTECODE=1 /tmp/pose-qa-venv/bin/python model/tools/check_weights.py
NODE_PATH=/private/tmp/pose-model-validator/node_modules node model/tools/validate_glb.cjs
GLTF_VALIDATOR_NODE_PATH=/private/tmp/pose-model-validator/node_modules PYTHONDONTWRITEBYTECODE=1 /tmp/pose-qa-venv/bin/python -m pytest tests -q -p no:cacheprovider
```

The venv is created by `scripts/run_female_qa.sh` (`tests/requirements.txt`); the validator is `npm i gltf-validator` in `/private/tmp/pose-model-validator`.

`build_female.py` runs the fixed-topology base morph (`make_female.py`), saves `validation/female_before_breast_refinement.glb`, remeshes the chest (`refine_chest.py`) and writes generation diagnostics. Generation is deterministic: two consecutive builds give the same file, SHA-256 `3063067122b2b17a8bc10de0010429e755e275969de8a91c6ce55a9715f54da5`.

Pipeline:

```
male.glb → make_female.py (proportions, 0.925 scale) → female_before_breast_refinement.glb
        → refine_chest.py (chest-front remesh, side fans, normals, mapping) → female.glb + chest_vertex_mapping.json + breast_metrics.json
        → measure_refined.py (hull girths) → validation.json
```

## Construction (`model/tools/refine_chest.py`)

The connected chest shell is a closed box of 60 welded positions / 116 triangles. Its **front patch** (both halves, 40 source triangles, including the old bottom rim) is replaced. The patch boundary is made of original shell edges, so the sides, back and top of the shell keep their original faces.

1. **Chest wall.** Smoothing thin-plate spline (λ = 2e-6) through dense samples of the original front faces. This removes the coarse-face creases without the overshoot of a pure interpolating spline.
   - Only the last 3 cm of the plate (y 1.185 → 1.152) is rounded back towards the abdomen shell, removing 80% of the old overhang. The retreat is bounded by the abdomen front within ±3 cm + 0.8 mm.
   - The under-bust girth above that zone is kept.
2. **Breast displacement.** Teardrop footprint `R(θ)` around (±0.079, 1.274): lateral 62, upper-lateral 86, up 94, upper-medial 84, medial 62, lower-medial 84, down 78, lower-lateral 82 mm. There are three profiles:
   - Upper pole: `(1-ρ)^3.2 (1+3.2ρ+3.5ρ²)`, a round top, then a straight-to-concave slope that fades into the upper chest with zero slope.
   - Medial/lateral sides: `(1-ρ^2.2)^1.4`, a broad round top fading with zero slope, so there is no ball-on-wall edge.
   - Lower pole: `1-ρ^2.2`, full and convex. It meets the wall at the IMF with a finite slope, which makes a readable but soft fold (dihedral ≤ 50°).

   The upper and lower profiles take over beyond |sin θ| = 0.2. Peak displacement is 41 mm along the breast axis, which leans 12° laterally.
3. **Apex and rings.**
   - The apex is the most projecting point along the breast axis, not the displacement centre (the source upper chest leans back).
   - It is finished by a **flat 8-sided cap**: eight points at the same axial height 2.5 mm below the apex, so exactly planar, about 1.8–2.7 cm across.
   - An 8-sided loop follows, then five 16-sided loops (levels .81/.64/.46/.28/.12/0 of the apex height, normalised per direction to the footprint edge). Loops near the apex therefore keep 8 sides, and 16 spokes no longer converge on one point.
   - Equal loops are joined by quads, and the single 8→16 step by three triangles per inner edge.
4. **Outer flow.** A plain wall ring sits halfway out, then each footprint vertex runs to its closest point on the shell boundary: sternum, upper chest/axilla, side and under-bust edge. Runs are smoothed along the loop, so edges meet the boundary roughly at right angles and fan gradually round corners. Original boundary vertices are kept.
5. **Rim strip.** It joins the new under-bust edge (points above the original bottom-edge vertices and the old plate corner) to the original bottom edge, and tucks under like the source plate.
6. **Abdomen clearance.** The top of the abdomen shell sits inside the chest bottom. Every new front face is sampled over the abdomen's flat front (|x| < 0.08). Free vertices are lifted by a capped least-norm amount until each sampled face point clears the actual abdomen triangles by ≥ 0.8 mm. v4 has no separate IMF fold: the IMF comes from the lower profile, and the old 4.7 mm fold reduced the under-bust girth.
7. **Seams.** Side and top faces sharing a boundary edge that received new points are fanned through those points. The points lie on the original straight edge, so the fans stay in the original plane and no T-junction is created.
8. **Shading, symmetry, attributes.**
   - Every new polygon has its own vertices with its flat face normal, like the faceted source. The cap is one flat face.
   - Quad diagonals are chosen on the right half and mirrored, so the left half is the exact mirror image.
   - UV, JOINTS_0 and WEIGHTS_0 of new vertices are barycentrically interpolated from the source front triangle under them, on the correct side (per joint ID, top four renormalised).
   - Kept and fanned original chest faces get flat normals recomputed per source smoothing group.

Final GLB: one mesh, two material primitives sharing one canonical vertex pool (a reader must deduplicate shared accessors when counting vertices).

| Canonical indices, inclusive | Source correspondence |
|---|---|
| 0–2857 | Male Body local 0–2857 |
| 2858–4105 | Male Joints local 0–1247, plus 2858 |
| **4106–5211** | **1,106 appended chest vertices** (per-face flat-shading copies) |

Total **5,212 vertices / 2,566 triangles** (v3: 5,338 / 2,632; v2: 10,847 / 13,572).

The chest shell has **594 triangles** (source 116, v2 11,600, v3 660). Per half there are 252 patch triangles:
- 174 inside each breast footprint: cap 6, cap→8-loop 16, 8→16 step 24, four 16-loop bands 128.
- 32 in the wall-ring band.
- 46 in the outer runs and rim strip.

The remaining 90 chest triangles are the 76 kept back/side/top originals plus the side/top fans. Every original non-chest position, UV, joint and weight is unchanged. The 80 original chest attribute vertices of the old front interior are no longer referenced by triangles; they stay in the pool at their original indices, placed on the new surface. `validation/chest_vertex_mapping.json` lists each appended index with three original canonical parents and barycentric weights, `triangle_source` (final triangle → original male triangle) and the unreferenced original indices.

## Form measurements

Two methods are reported. The generator method (`validation/breast_metrics.json`) compares the final surface with the same mesh at zero breast displacement, i.e. against the real chest wall. The QA method (`validation/qa_bust_v2.json`, from `tests/bust_eval.py`) uses a 2 mm heightfield and a quadratic wall fitted 12–17 cm around the detected apex.

| Metric | Generator (vs. real wall) | QA method (left / right) |
|---|---:|---:|
| Apex (most projecting point, cap centre) | x ±0.0854, y 1.2635 m | x ±0.094, y 1.266 m |
| Apex relative height (bottom 0, top 1) | **0.44** (excess > 3 mm: y 1.200–1.344) | 0.500 / 0.500 |
| Projection | **43.8 mm** at the apex (max 49.1 mm) | 62.0 / 62.3 mm |
| One breast volume | 336 cm³ | 450.5 / 456.6 cm³ |
| Upper-pole volume fraction | 0.526 | 0.470 / 0.469 |
| Outward facing (yaw from +Z) | apex (cap) normal **12.0°**, base-centroid→apex **5.8°** (v3 4.7°) | — |
| Apex normal pitch | 0° (level) | — |
| IMF | y 1.196 m; QA lower/upper wall angle 51.0° / 35.9° | — |
| Bust − underbust | **15.8 cm** (102.5 at apex height − 86.7 at IMF − 1 cm) | 23.3 cm (102.7 @ 1.266 − 79.4 @ 1.148) |

Other QA values: roundness 0.82; max dihedral 50.2°; midline curvature 12.2 /m; cleavage excess 6.2 mm; bridge 0; sternum ridge 1.1 mm; abdomen poke −9.2 mm; new chest-partner faces with upper arm / waist band / abdomen 0 / 0 / 0. Shoulder/hip ratio 0.990 and WHR 0.741 are unchanged.

## Test results

Full command (`validation/pytest_v4_output.txt`): **104 passed, 5 skipped, 4 failed**, all failures in `test_08_bust.py`. Tests were run, not edited. The skips are the existing coarse-chest/seam skips and the retired waist/bust criterion.

| Failing test | Value | Classification |
|---|---|---|
| `test_apex_is_below_breast_mid_height` | 0.500 | **QA measurement artifact.** Every vertex below the IMF has zero breast displacement, but the QA quadratic wall leaves +6…+10 mm "excess" on the under-bust plate corner (x 0.06–0.08, y 1.16), which must stay in front of the abdomen shell. The detected breast spans the whole ±0.108 m disc, which gives 0.5 exactly. Against the real wall the apex is at 0.44. |
| `test_lower_contour_is_convex_and_fuller_than_upper` | −0.10 | Same artifact: the lower chord starts at y 1.158, 4 cm below the IMF, on the flat plate. |
| `test_cup_girth_difference_14_to_16_cm` | 23.3 cm | **QA measurement artifact.** The underbust is taken at y 1.148, inside the bottom tuck under the abdomen. At the real IMF − 1 cm the difference is **15.8 cm**, inside 14–16 (v3: 18.4). |
| `test_no_single_vertex_cone_spike` | 17.8 mm at (±0.076, 1.152) | **Intended by the low-poly requirement.** It is the corner vertex where the under-bust edge meets the plate's bottom bevel, a faceted crease. It is in the QA box only because of the artifact above. |

These now pass:
- `test_no_steps_or_notches_at_lower_chest_edge` (12 edges / 0.43 m ≤ 0.52 m; v3 failed at 0.54 m).
- `test_left_right_symmetry`. Exact mirroring is now enforced; an intermediate v4 build had failed it at 4.0% volume.
- Volume, projection, upper-pole fraction, upper contour, IMF angle, maximum dihedral, roundness, cleavage, bridge, midline ridge, no new intersections, topology, seams, attributes and non-chest preservation.

Official glTF validator: **0 errors, 1 warning, 2 infos** (unchanged in kind): the retained JOINTS/WEIGHTS on an intentionally unskinned static base, and unused UVs on untextured primitives.

Independent checks (`verify.py` → `validation/refined_checks.json`):
- 0 degenerate triangles; 0 displaced-breast collisions.
- Lowered-arm proxy (30/40/45°): 0 breast contacts and 0 new pairs due to breast volume; chest–arm source pairs 48/56/64 equal the zero-displacement control.
- The check reports 6 "new" chest source pairs (neck 3, shoulder 2, abdomen 1). These are a relabelling effect: the sets of neck, shoulder and abdomen faces intersected by the chest are identical, by vertex triple, to both the pre-refinement base and v2, and the upper-arm set equals v2's 4 faces.

## Skin weights (`model/tools/check_weights.py` → `validation/chest_weight_check.json`)

The rigger owns the weights; they are reported here, not repainted.
- **Source.** The source chest shell is rigidly weighted: each vertex has 100% on one of DEF-spine.002 / .003 / .004, by horizontal rows.
- **Appended vertices.** All 1,106 interpolate those rows and have at most two influences.
- **Shoulder/arm leakage.** Spine share is 100%; shoulder / upper-arm / forearm / hand share is exactly 0 everywhere, including the 616 vertices of the breast mounds (|x| 0.02–0.14, y 1.19–1.37, z > 0.06).
- **By height in the mounds:**

| Height y | Weights |
|---|---|
| 1.19–1.22 (lower pole) | spine.002 51% / spine.003 49% |
| 1.22–1.25 | spine.002 28% / spine.003 72% |
| ≥ 1.25 | spine.003 95–100% |

- **Note for the rigger.** The lower pole is half on spine.002 (the abdomen bone), so bending the spine will shear it. For an arms-up pose, a pectoral/shoulder influence on the upper-lateral breast may also be wanted. Neither was changed here.

## Previews

`previews/female_front.png`, `female_side.png`, `female_three_quarter.png` and `female_chest_side.png` use geometric face normals. They were re-rendered and inspected next to the male previews:
- **Apex.** In front and three-quarter views each breast reads as a rounded faceted mass. There is no 16-spoke star; the apex ends in a small flat 8-sided facet.
- **Side.** The side view shows a straight-to-concave upper pole, a full lower pole and a soft IMF.
- **Bottom edge.** It is a thin bevel, overhanging the abdomen front by 3.5 mm at the centre (v3 7.8 mm, source 12.5 mm).
- **Facets.** Facet size matches the head/hands of the body.

## Remaining limitations

- **QA artifacts.** The QA quadratic wall cannot represent the mannequin's flat chest plate with its turned corner, so three QA shape tests fail although the real-wall measurements meet the intent.
- **Upper-pole fraction.** Against the real wall it is 0.526, slightly above 0.5. QA reads 0.47. The upper chest leans back under the upper pole.
- **Apex look.** Under the top-left preview light, the three-quarter view still shows the apex cap as a small light facet with darker lower facets beneath. That is ordinary dome shading at this facet density, not a pinch.
- **Base-centroid axis.** The base-centroid→apex yaw is only 5.8°: the lateral footprint lies far back on the turning wall. More lean would widen the bust girth again.
- **Slivers.** A few long, thin triangles remain in the outer runs near the upper sternum and the axilla corners (flat wall).
- **No real skinning check.** This is an unskinned base: arm-lowering is a rigid proxy, and fitted-skeleton poses need rigger validation.

## History

Earlier generators, outputs and logs are kept in `validation/prior_revision/`:
- `v2/`: smooth subdivided chest.
- `v3/`: first faceted remesh with the 16-spoke apex, `refine_chest_v3.py` and logs.

`qa_bust_v2.json` in `validation/` is the current file; the name comes from `qa_bust_summary.py`.

## Attribution

Source author: **RD3D Game Design**. Source: [UE Mannequin Demake](https://sketchfab.com/3d-models/ue-mannequin-demake-929c983369ec435196a215d29dd6d907). License: **CC BY 4.0**, as recorded in `male.glb`. Female modifications: feminine proportions, 7.5% height reduction, chest remesh and breast/ribcage shaping. Original attribution/license metadata is preserved.
