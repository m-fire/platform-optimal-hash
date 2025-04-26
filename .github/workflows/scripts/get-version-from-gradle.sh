#!/bin/bash
# gradle.properties 에서 libVersion 값을 읽어 릴리스 버전 정보 설정

set -e # 오류 발생 시 즉시 종료

REPO_ROOT="$(cd "$(dirname "$0")/../../.." && pwd)" # 스크립트 위치 기준 저장소 루트
GRADLE_PROPERTIES_PATH="$REPO_ROOT/gradle.properties"

echo "==== 릴리스 버전 결정 시작 (from gradle.properties) ===="

# --- 현재 버전 읽기 (gradle.properties) ---
echo "버전 읽는 중 (from ${GRADLE_PROPERTIES_PATH})..."
if [ ! -f "$GRADLE_PROPERTIES_PATH" ]; then
    echo "::error::gradle.properties 파일을 찾을 수 없습니다 (${GRADLE_PROPERTIES_PATH})."
    exit 1
fi
current_version=$(grep -E '^\s*libVersion\s*=' "$GRADLE_PROPERTIES_PATH" | sed -E 's/^\s*libVersion\s*=\s*(.*)\s*/\1/')
if [[ -z "$current_version" ]]; then
  echo "::error::libVersion not found in gradle.properties"
  exit 1
fi
echo "읽어온 libVersion: $current_version"

# --- 출력값 설정 ---
# 'v' 접두사 제거 -> version_num
version_num=${current_version#v}
# 'v' 접두사 추가 -> version_tag
version_tag="v${version_num}"

echo "결정된 version_num: $version_num"
echo "결정된 version_tag: $version_tag"

# 워크플로우에서 사용할 수 있도록 출력 설정
if [ -n "$GITHUB_OUTPUT" ]; then
  echo "version_num=${version_num}" >> "$GITHUB_OUTPUT"
  echo "version_tag=${version_tag}" >> "$GITHUB_OUTPUT"
else
  echo "경고: GITHUB_OUTPUT 환경 변수가 설정되지 않아 출력을 설정할 수 없습니다."
fi

echo "==== 릴리스 버전 결정 완료 ===="
