#!/bin/bash
# 다운로드된 빌드 아티팩트에서 최종 릴리스 에셋 준비 (파일명 통일)

set -e # 오류 발생 시 즉시 종료

# 입력: 아티팩트가 다운로드된 경로, 출력 에셋 경로
ARTIFACTS_DIR=${1:-"downloaded-artifacts"}
OUTPUT_DIR=${2:-"release-assets"}

REPO_ROOT="$(cd "$(dirname "$0")/../../.." && pwd)" # 스크립트 위치 기준 저장소 루트

echo "==== 릴리스 에셋 준비 시작 ===="
echo "입력 아티팩트 경로: ${ARTIFACTS_DIR}"
echo "출력 에셋 경로: ${OUTPUT_DIR}"

# --- 바이너리 파일명 추출 (from gradle.properties) ---
GRADLE_PROPERTIES_PATH="$REPO_ROOT/gradle.properties"
echo "바이너리 파일명 추출 중 (from ${GRADLE_PROPERTIES_PATH})..."
BINARY_FILENAME="" # 변수 초기화

if [ ! -f "$GRADLE_PROPERTIES_PATH" ]; then
    echo "오류: gradle.properties 파일을 찾을 수 없습니다 (${GRADLE_PROPERTIES_PATH})." >&2
    exit 1
else
    BINARY_FILENAME=$(grep -E '^\s*binaryFilename\s*=' "$GRADLE_PROPERTIES_PATH" | grep -v '^\s*#' | sed -E 's/^\s*binaryFilename\s*=\s*(.*)\s*/\1/' | head -n 1)
fi

if [ -z "$BINARY_FILENAME" ]; then
  echo "오류: gradle.properties 에서 binaryFilename 값을 추출하지 못했습니다." >&2
  exit 1
fi
echo "기준 바이너리 파일명: ${BINARY_FILENAME}"

# --- 출력 디렉토리 준비 ---
rm -rf "${OUTPUT_DIR}"
mkdir -p "${OUTPUT_DIR}"
echo "출력 디렉토리 생성 완료: ${OUTPUT_DIR}"

# --- 아티팩트 검색 및 파일명 통일하여 복사 ---
echo "아티팩트 검색 및 에셋 복사/이름 변경 시작..."

# 확장자별 처리 (플랫폼 구분 없이 확장자 기준으로 대표 파일 하나씩 찾기)
declare -A extensions=( [so]="linuxX64 androidNativeArm64 androidNativeX64" [dylib]="macosArm64 macosX64 iosArm64 iosX64" [dll]="windowsX64" )
declare -A found_map

for ext in "${!extensions[@]}"; do
  target_filename="${BINARY_FILENAME}.${ext}"
  echo "처리 중: 확장자 .${ext} -> 목표 파일명 ${target_filename}"
  found_in_ext=0

  # find 명령어 개선: downloaded-artifacts 전체에서 해당 패턴 검색
  # -iname: 대소문자 무시, -type f: 파일만, -print: 경로 출력, -quit: 하나 찾으면 종료
  src_file=$(find "${ARTIFACTS_DIR}" -type f -iname "*${BINARY_FILENAME}*.${ext}" -print -quit)

  if [ -n "$src_file" ]; then
      echo "  발견된 원본 파일: ${src_file}"
      cp "$src_file" "${OUTPUT_DIR}/${target_filename}"
      echo "  복사 및 이름 변경 완료: ${OUTPUT_DIR}/${target_filename}"
      found_map[$ext]=1
      found_in_ext=1
  fi

  if [ $found_in_ext -eq 0 ]; then
      echo "  경고: 확장자 .${ext} 를 가진 '${BINARY_FILENAME}' 포함 파일을 찾지 못했습니다."
  fi
done

# --- 결과 확인 ---
echo "최종 에셋 목록 (${OUTPUT_DIR}):"
ls -l "${OUTPUT_DIR}"

# 모든 주요 확장자 파일이 준비되었는지 확인 (선택적)
if [[ -z "${found_map[so]}" || -z "${found_map[dylib]}" || -z "${found_map[dll]}" ]]; then
 echo "경고: 일부 플랫폼의 바이너리가 최종 에셋에 포함되지 않았을 수 있습니다."
fi

echo "==== 릴리스 에셋 준비 완료 ===="
