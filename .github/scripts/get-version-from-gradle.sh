#!/bin/bash
# .github/scripts/get-version-from-gradle.sh
# 설명: gradle.properties 에서 libVersion 값을 읽고 형식을 검증한 후 GitHub Actions 출력으로 설정

# 오류 발생 시 즉시 종료
set -e
# 디버깅 필요 시: set -x

# 스크립트가 위치한 디렉토리 기준 저장소 루트 경로 계산
REPO_ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
GRADLE_PROPERTIES_PATH="$REPO_ROOT/gradle.properties"

echo "==== 릴리스 버전 결정 시작 (from gradle.properties) ===="
echo "저장소 루트: ${REPO_ROOT}"
echo "Gradle 속성 파일 경로: ${GRADLE_PROPERTIES_PATH}"

# --- gradle.properties 파일 존재 확인 ---
if [ ! -f "$GRADLE_PROPERTIES_PATH" ]; then
    echo "::error::gradle.properties 파일을 찾을 수 없습니다 (${GRADLE_PROPERTIES_PATH})."
    exit 1
fi
echo "Gradle 속성 파일 확인 완료."

# --- libVersion 읽기 ---
# grep: 'libVersion'으로 시작하는 줄 찾기 (공백 허용)
# sed: '=' 앞뒤 공백 및 'libVersion=' 제거하여 값만 추출
current_version_raw=$(grep -E '^\s*libVersion\s*=' "$GRADLE_PROPERTIES_PATH" | sed -E 's/^\s*libVersion\s*=\s*(.*)\s*/\1/')

if [[ -z "$current_version_raw" ]]; then
  echo "::error::gradle.properties 파일에서 libVersion을 찾을 수 없습니다."
  exit 1
fi
echo "읽어온 libVersion (Raw): '${current_version_raw}'" # 따옴표로 감싸서 공백 확인 용이하게 함

# --- libVersion 형식 검증 (Trim Check) ---
# sed를 사용하여 앞뒤 공백 제거
trimmed_version=$(echo "$current_version_raw" | sed -e 's/^[[:space:]]*//' -e 's/[[:space:]]*$//')
echo "Trimmed libVersion: '${trimmed_version}'"

if [[ "$current_version_raw" != "$trimmed_version" ]]; then
  echo "::error::libVersion 값 (${current_version_raw})에 불필요한 앞뒤 공백이 포함되어 있습니다. 공백을 제거해 주세요."
  exit 1
fi
echo "libVersion 형식 검증 완료."

# --- 출력값 설정 (Trimmed 버전 기준) ---
# 'v' 접두사 제거 -> version_num
version_num=${trimmed_version#v}
# 'v' 접두사 추가 -> version_tag
version_tag="v${version_num}"

echo "결정된 version_num: ${version_num}"
echo "결정된 version_tag: ${version_tag}"

# --- GitHub Actions 출력 설정 ---
# GITHUB_OUTPUT 환경 변수가 설정되어 있는지 확인 (Actions 환경에서만 유효)
if [ -n "$GITHUB_OUTPUT" ]; then
  echo "GitHub Actions 출력 설정 중..."
  echo "version_num=${version_num}" >> "$GITHUB_OUTPUT"
  echo "version_tag=${version_tag}" >> "$GITHUB_OUTPUT"
  echo "출력 설정 완료."
else
  # 로컬 실행 등 GITHUB_OUTPUT이 없는 경우 경고
  echo "::warning::GITHUB_OUTPUT 환경 변수가 설정되지 않아 출력을 설정할 수 없습니다. Actions 환경 외부에서 실행되었을 수 있습니다."
fi

echo "==== 릴리스 버전 결정 완료 ===="
