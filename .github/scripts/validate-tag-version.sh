#!/bin/bash
# .github/scripts/validate-pr-version.sh
# 설명: PR 시 gradle.properties의 libVersion 값을 trim하여 최신 릴리스 태그보다 높은지 검증

# 오류 발생 시 즉시 종료
set -e
# 디버깅 필요 시: set -x

# 입력: 최신 릴리스 태그 (환경 변수로 전달받음)
LATEST_RELEASE_TAG_RAW="${INPUT_LATEST_RELEASE_TAG:-"0.0.0"}" # 기본값 설정

# 스크립트가 위치한 디렉토리 기준 저장소 루트 경로 계산
REPO_ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
GRADLE_PROPERTIES_PATH="$REPO_ROOT/gradle.properties"

echo "==== PR 버전 유효성 검증 시작 ===="
echo "저장소 루트: ${REPO_ROOT}"
echo "Gradle 속성 파일 경로: ${GRADLE_PROPERTIES_PATH}"
echo "입력된 최신 릴리스 태그 (Raw): ${LATEST_RELEASE_TAG_RAW}"

# --- gradle.properties 파일 존재 확인 ---
if [ ! -f "$GRADLE_PROPERTIES_PATH" ]; then
    echo "::error::gradle.properties 파일을 찾을 수 없습니다 (${GRADLE_PROPERTIES_PATH})."
    exit 1
fi
echo "Gradle 속성 파일 확인 완료."

# --- 현재 버전 읽기 (gradle.properties) ---
echo "현재 버전 읽는 중..."
current_version_raw=$(grep -E '^\s*libVersion\s*=' "$GRADLE_PROPERTIES_PATH" | sed -E 's/^\s*libVersion\s*=\s*(.*)\s*/\1/')
if [[ -z "$current_version_raw" ]]; then
  echo "::error::gradle.properties 파일에서 libVersion을 찾을 수 없습니다."
  exit 1
fi
echo "현재 버전 (libVersion Raw): '${current_version_raw}'"

# --- libVersion 값 Trim ---
# sed를 사용하여 앞뒤 공백 제거
trimmed_version=$(echo "$current_version_raw" | sed -e 's/^[[:space:]]*//' -e 's/[[:space:]]*$//')
echo "Trimmed libVersion: '${trimmed_version}'"

# --- 버전 비교를 위한 숫자 부분 추출 (Trimmed 버전 기준) ---
current_version_num=${trimmed_version#v}
echo "현재 버전 (Numeric, Trimmed): ${current_version_num}"

# --- 최신 릴리스 태그 버전 처리 ---
latest_tag_num=${LATEST_RELEASE_TAG_RAW#v} # 'v' 접두사 제거
echo "최신 릴리스 태그 (Numeric): ${latest_tag_num}"

# --- 버전 비교 검증 (Trimmed 버전 기준) ---
echo "버전 비교 중: 현재(${current_version_num}) vs 최신 릴리스(${latest_tag_num})"

# Semantic Versioning 비교를 위해 sort -V 사용
highest_version=$(printf '%s\n' "$current_version_num" "$latest_tag_num" | sort -V | tail -n 1)

if [[ "$current_version_num" == "$latest_tag_num" ]]; then
  # 버전이 동일한 경우
  echo "::error::현재 libVersion (${trimmed_version})이 최신 릴리스 태그 (${LATEST_RELEASE_TAG_RAW})와 동일합니다. gradle.properties의 버전을 증가시켜야 합니다."
  exit 1
elif [[ "$current_version_num" != "$highest_version" ]]; then
  # 현재 버전이 최신 릴리스보다 낮은 경우
   echo "::error::현재 libVersion (${trimmed_version})은 최신 릴리스 태그 (${LATEST_RELEASE_TAG_RAW})보다 높아야 합니다."
   exit 1
fi

# 여기까지 오면 현재 버전이 최신 릴리스보다 높음
echo "버전 증가 유효성 검증 성공: 현재 버전(${current_version_num})이 최신 릴리스(${latest_tag_num})보다 높습니다."
echo "==== PR 버전 유효성 검증 완료 ===="
