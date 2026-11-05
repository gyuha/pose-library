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

Tools: Blender 3.5.1 bundled Python 3.10 / NumPy, plus a deterministic NumPy orthographic triangle rasterizer (z-buffer, interpolated normals, diffuse light, no OpenGL). The installed Blender application crashes during startup even with `--factory-startup`, so its standalone bundled interpreter is used instead. Any Python 3 with NumPy can run these scripts.

From the repository root:

```sh
/Applications/Blender.app/Contents/Resources/3.5/python/bin/python3.10 model/tools/make_female.py
/Applications/Blender.app/Contents/Resources/3.5/python/bin/python3.10 model/tools/render_previews.py
/Applications/Blender.app/Contents/Resources/3.5/python/bin/python3.10 model/tools/verify.py
npm install --prefix /private/tmp/pose-model-validator --cache /private/tmp/pose-model-npm-cache gltf-validator
NODE_PATH=/private/tmp/pose-model-validator/node_modules node model/tools/validate_glb.cjs
```

The deformation narrows shoulders, waist, neck and arms; tapers the head/jaw; adds paired anterior chest volumes, broader hips, posterior gluteal volume and fuller upper thighs. Overall scale is 0.925 about the floor origin. Normals use the inverse transpose of the deformation Jacobian. No manual editing, mesh subdivision, export round-trip or remeshing is involved.

Female has two identity mesh nodes, Y-up, the same origin and materials. Its old male skin/skeleton is intentionally removed: this is an **unskinned base for the rigger**, not an animation-ready rig. Original JOINTS_0 / WEIGHTS_0 data and unused inverse-bind accessor are retained for reference; they do not constitute an active female binding. The rigger must fit joint positions and bind matrices for the new proportions; exact vertex/index correspondence supports weight transfer.

## Validation

- Official `gltf-validator` 2.0.0-dev.3.10: female **0 errors, 2 warnings, 3 informational messages**. Warnings are `NODE_SKINNED_MESH_WITHOUT_SKIN` on the two deliberately static meshes with retained source joint attributes. Informational messages are unused UVs (no textures) and unused original inverse-bind accessor. Male: 0 errors, 2 warnings, 3 infos. Full reports are included.
- Index arrays and source UV/joint/weight arrays compare exactly. Direct in-place POSITION/NORMAL buffer writes preserve vertex correspondence. Both models: **4,106 vertices / 2,088 triangles**.
- Female bbox min `[-0.61758132, -0.0000000284, -0.16478109]`, max `[0.61758232, 1.75748553, 0.17087710]` m.
- Height: male **1.89998436 m**, female **1.75748556 m**, ratio **0.925000015**, reduction **7.5%**.
- No nonfinite position/normal values, **0 degenerate triangles**, **0 triangle-normal reversals** relative to source. Minimum sampled deformation Jacobian determinant: Body **0.393375**, Joints **0.420801**, both positive.
- Strict noncoplanar triangle intersection check: male **1,369 pairs**, female **1,386 pairs**, **67 new / 50 resolved**. This includes intersecting disconnected mannequin shells and joint components. Endpoints, shared edges and coplanar contacts are excluded. This is a diagnostic, not proof of an intersection-free or watertight mesh. Existing and newly shifted overlaps remain; inspect articulations when rigging.
- `previews/{male,female}_{front,side,three_quarter}.png`: same orthographic scale and camera setup. Female front, side and 3/4 images were opened and inspected. Chest projection, waist/hip contrast, narrower shoulders and fuller thighs are visible; no large inverted patches or grossly broken surfaces were observed.

## Limits and attribution

This retains the source's faceted, segmented low-poly mannequin aesthetic. The very sparse chest and head topology limits round breasts, subtle facial detail and muscle smoothing; the face is featureless and the chest profile remains angular. Topology preservation precludes adding anatomical detail. The result is a stylized female base, not a realistic anatomical scan or clean continuous skin. Mesh overlaps remain as quantified above.

Source author: **RD3D Game Design**. Source: [UE Mannequin Demake](https://sketchfab.com/3d-models/ue-mannequin-demake-929c983369ec435196a215d29dd6d907). License: **CC BY 4.0**, as recorded in `male.glb` metadata. Female modification: procedural feminine proportions and 7.5% height reduction. Original author/license metadata is preserved in `female.glb`.
