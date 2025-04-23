#!/bin/bash
set -e

echo "===== 스크립트 유효성 테스트 시작 ====="

SCRIPTS_DIR="$(cd "$(dirname "$0")" && pwd)/scripts"

# 0. test-scripts.sh 자체 문법 체크
bash -n "./scripts-test.sh"
echo "[TEST] test-scripts.sh  - Syntax OK"

echo "[TEST] scripts/*.sh 문법 체크"
for script in "$SCRIPTS_DIR"/*.sh; do
  bash -n "$script"
  echo "  - Syntax OK: $(basename "$script")"
done

# 1. bump-gradle-version.sh dry-run (실제 파일 영향 없도록 임시 파일 사용)
echo "[TEST] bump-gradle-version.sh"
tmpfile="/tmp/build.gradle.kts.test"
echo 'version = "1.2.3"' > "$tmpfile"
cp "$tmpfile" "$tmpfile.bak"
(cd "$SCRIPTS_DIR/../.." && LIBRARY_FILE="$tmpfile" bash "$SCRIPTS_DIR/bump-gradle-version.sh" || true)
if grep -q 'version = "1.2.4"' "$tmpfile"; then
  echo "  - Version bump OK"
else
  echo "  - [FAIL] Version bump 실패"
fi
mv "$tmpfile.bak" "$tmpfile" # 복원

# 2. github-determine-version.sh
bash -n "$SCRIPTS_DIR/github-determine-version.sh"
echo "[TEST] github-determine-version.sh  - Syntax OK"
WORKFLOW_INPUT_VERSION="1.2.3" WORKFLOW_GITHUB_REF="" bash "$SCRIPTS_DIR/github-determine-version.sh"
WORKFLOW_INPUT_VERSION="" WORKFLOW_GITHUB_REF="refs/tags/v1.2.3" bash "$SCRIPTS_DIR/github-determine-version.sh"
if WORKFLOW_INPUT_VERSION="" WORKFLOW_GITHUB_REF="" bash "$SCRIPTS_DIR/github-determine-version.sh" 2>/dev/null; then
  echo "  - [FAIL] 입력값 누락 시 오류 미발생"
else
  echo "  - 입력값 누락 시 정상적으로 오류 발생"
fi

# 3. package-binaries.sh dry-run
bash -n "$SCRIPTS_DIR/package-binaries.sh"
echo "[TEST] package-binaries.sh  - Syntax OK"
VERSION="1.0.0" LIB_DIR="." OUTPUT_DIR="/tmp/test-output" bash "$SCRIPTS_DIR/package-binaries.sh" || echo "  - (경고) 빌드 산출물 없을 경우 경고 발생"

# 4. commit-push-binaries.sh 문법만 체크
bash -n "$SCRIPTS_DIR/commit-push-binaries.sh"
echo "[TEST] commit-push-binaries.sh  - Syntax OK (실행 생략)"

echo "===== 모든 스크립트 유효성 테스트 완료 ====="
