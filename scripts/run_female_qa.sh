#!/usr/bin/env bash
# female.glb QA 일괄 실행: 환경 준비 -> pytest -> 지표 JSON -> 근거 이미지.
# 사용: scripts/run_female_qa.sh            (venv 기본 위치: /tmp/pose-qa-venv, QA_VENV 로 변경 가능)
# 다른 파일 검사: FEMALE_GLB=/path/to/female.glb scripts/run_female_qa.sh
# 참고: 과제 문서의 Blender 번들 Python 경로는 이 머신에 없었다. numpy 가 있는 Python 3 이면 무엇이든 된다.
set -u
export PYTHONDONTWRITEBYTECODE=1   # tests/__pycache__ 가 git 에 섞이지 않게
cd "$(dirname "$0")/.."
VENV="${QA_VENV:-/tmp/pose-qa-venv}"
if [ ! -x "$VENV/bin/python" ]; then
  uv venv "$VENV" -q && uv pip install -q --python "$VENV/bin/python" -r tests/requirements.txt
fi
PY="$VENV/bin/python"
mkdir -p tests/reports tests/artifacts
# 결함이 있으면 pytest 는 실패(exit 1)한다. 그것이 정상 동작이므로 로그만 남기고 계속 진행한다.
"$PY" -m pytest tests -q -p no:cacheprovider --tb=line -rfs 2>&1 | tee tests/reports/pytest_output.txt
"$PY" scripts/dump_qa_metrics.py
"$PY" scripts/render_qa.py
