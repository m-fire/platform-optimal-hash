#!/bin/bash
# PR 시 gradle.properties의 libVersion과 최신 릴리스 태그를 비교하여 유효성 검증

set -e # 오류 발생 시 즉시 종료

# 입력: 최신 릴리스 태그 (환경 변수로 전달받음)
LATEST_RELEASE_TAG_RAW="${INPUT_LATEST_RELEASE_TAG:-"0.0.0"}" # 기본값 설정 (첫 릴리스 대비)

REPO_ROOT="$(cd "$(dirname "$0")/../../.." && pwd)" # 스크립트 위치 기준 저장소 루트
GRADLE_PROPERTIES_PATH="$REPO_ROOT/gradle.properties"

echo "==== 버전 유효성 검증 시작 ===="
echo "최신 릴리스 태그 (Raw): ${LATEST_RELEASE_TAG_RAW}"

# --- 현재 버전 읽기 (gradle.properties) ---
echo "현재 버전 읽는 중 (from ${GRADLE_PROPERTIES_PATH})..."
if [ ! -f "$GRADLE_PROPERTIES_PATH" ]; then
    echo "::error::gradle.properties 파일을 찾을 수 없습니다 (${GRADLE_PROPERTIES_PATH})."
    exit 1
fi
current_version=$(grep -E '^\s*libVersion\s*=' "$GRADLE_PROPERTIES_PATH" | sed -E 's/^\s*libVersion\s*=\s*(.*)\s*/\1/')
if [[ -z "$current_version" ]]; then
  echo "::error::libVersion not found in gradle.properties"
  exit 1
fi
# 'v' 접두사 제거
current_version_num=${current_version#v}
echo "현재 버전 (Numeric): ${current_version_num}"


# --- 최신 릴리스 태그 버전 처리 ---
latest_tag_num=${LATEST_RELEASE_TAG_RAW#v} # 'v' 접두사 제거
echo "최신 릴리스 태그 (Numeric): ${latest_tag_num}"


# --- 버전 비교 검증 ---
echo "버전 비교 중: ${current_version_num} vs ${latest_tag_num}"

# 동일 버전 또는 낮은 버전인지 확인
if [[ "$current_version_num" == "$latest_tag_num" ]]; then
  echo "::error::Current libVersion ($current_version) is the same as the latest release tag ($LATEST_RELEASE_TAG_RAW). Please increment the version in gradle.properties."
  exit 1
fi

# sort -V 를 사용하여 버전 비교 (현재 버전이 더 커야 함)
# 두 버전을 정렬했을 때 현재 버전이 마지막에 오지 않으면 오류
highest_version=$(printf '%s\n' "$current_version_num" "$latest_tag_num" | sort -V | tail -n 1)
if [[ "$current_version_num" != "$highest_version" ]]; then
   echo "::error::Current libVersion ($current_version) must be higher than the latest release tag ($LATEST_RELEASE_TAG_RAW)."
   exit 1
fi

echo "버전 유효성 검증 성공: ${current_version_num} > ${latest_tag_num}"
echo "==== 버전 유효성 검증 완료 ===="
