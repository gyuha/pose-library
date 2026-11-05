"""(a) GLB 유효성: 컨테이너 구조, accessor 범위, NaN/Inf, 법선 단위길이, 퇴화 삼각형, 공식 gltf-validator."""
import json
import os
import shutil
import subprocess
from pathlib import Path

import numpy as np
import pytest

from glb_io import FEMALE, MALE, Model, accessor, read_glb

COMPONENT_SIZE = {5120: 1, 5121: 1, 5122: 2, 5123: 2, 5125: 4, 5126: 4}
TYPE_N = {"SCALAR": 1, "VEC2": 2, "VEC3": 3, "VEC4": 4, "MAT4": 16}


@pytest.mark.parametrize("path", [MALE, FEMALE], ids=["male", "female"])
def test_accessors_within_buffer(path):
    g, buf = read_glb(path)
    assert len(g["buffers"]) == 1 and g["buffers"][0]["byteLength"] <= len(buf)
    for ai, a in enumerate(g["accessors"]):
        if "bufferView" not in a:
            continue
        v = g["bufferViews"][a["bufferView"]]
        el = COMPONENT_SIZE[a["componentType"]] * TYPE_N[a["type"]]
        stride = v.get("byteStride", el)
        end = v.get("byteOffset", 0) + a.get("byteOffset", 0) + stride * (a["count"] - 1) + el
        assert end <= v["byteOffset"] + v["byteLength"] if "byteOffset" in v else end <= v["byteLength"], f"accessor {ai} 범위 초과"
    for m in g["meshes"]:
        p = m["primitives"][0]
        n = g["accessors"][p["attributes"]["POSITION"]]["count"]
        idx = accessor(g, buf, p["indices"]).ravel()
        assert idx.max() < n and len(idx) % 3 == 0, "인덱스 범위/삼각형 수 오류"


@pytest.mark.parametrize("path", [MALE, FEMALE], ids=["male", "female"])
def test_all_floats_finite_and_normals_unit(path):
    g, buf = read_glb(path)
    for a_i, a in enumerate(g["accessors"]):
        if a["componentType"] == 5126:
            assert np.isfinite(accessor(g, buf, a_i)).all(), f"accessor {a_i} 에 NaN/Inf"
    m = Model(path)
    assert np.abs(np.linalg.norm(m.nrm, axis=1) - 1).max() < 1e-4, "단위 길이가 아닌 NORMAL"


def test_position_accessor_minmax_matches_data():
    g, buf = read_glb(FEMALE)
    for mesh in g["meshes"]:
        ai = mesh["primitives"][0]["attributes"]["POSITION"]
        P = accessor(g, buf, ai)
        a = g["accessors"][ai]
        assert np.allclose(P.min(0), a["min"], atol=1e-6) and np.allclose(P.max(0), a["max"], atol=1e-6), \
            "POSITION accessor min/max 가 실제 데이터와 불일치 (스펙 위반)"


def test_no_degenerate_triangles():
    f = Model(FEMALE)
    area = np.linalg.norm(np.cross(f.pos[f.tri[:, 1]] - f.pos[f.tri[:, 0]], f.pos[f.tri[:, 2]] - f.pos[f.tri[:, 0]]), axis=1) / 2
    assert (area > 1e-9).all(), f"퇴화 삼각형 {int((area <= 1e-9).sum())}개"


def _validator_report(path):
    """gltf-validator(node 모듈)가 있으면 실행, 없으면 skip. 모듈 위치: $GLTF_VALIDATOR_NODE_PATH 또는 /private/tmp/pose-model-validator/node_modules"""
    node = shutil.which("node")
    nm = os.environ.get("GLTF_VALIDATOR_NODE_PATH", "/private/tmp/pose-model-validator/node_modules")
    if not node or not (Path(nm) / "gltf-validator").exists():
        pytest.skip("node 또는 gltf-validator 모듈 없음 (npm i gltf-validator 후 GLTF_VALIDATOR_NODE_PATH 지정)")
    js = ("const v=require('gltf-validator'),fs=require('fs');"
          "v.validateBytes(new Uint8Array(fs.readFileSync(process.argv[1])),{maxIssues:1000})"
          ".then(r=>console.log(JSON.stringify(r.issues)))")
    out = subprocess.run([node, "-e", js, str(path)], env={**os.environ, "NODE_PATH": nm},
                         capture_output=True, text=True, check=True).stdout
    return json.loads(out)


@pytest.mark.parametrize("path", [MALE, FEMALE], ids=["male", "female"])
def test_official_gltf_validator_no_errors(path):
    issues = _validator_report(path)
    assert issues["numErrors"] == 0, [m for m in issues["messages"] if m["severity"] == 0]
