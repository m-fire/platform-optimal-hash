#!/bin/bash
# release-assets 디렉토리 내용을 기반으로 동적 릴리스 본문 생성

set -e # 오류 발생 시 즉시 종료

# 입력: 릴리스 버전 태그, 에셋 디렉토리 경로, 출력 파일 경로 (환경 변수)
VERSION_TAG="${INPUT_VERSION_TAG}"
ASSETS_DIR="${INPUT_ASSETS_DIR:-release-assets}"
OUTPUT_FILE="${OUTPUT_BODY_FILE:-.github/release-body.md}" # 워크플로우 루트 기준 경로

echo "==== 릴리스 본문 생성 시작 ===="
echo "버전 태그: ${VERSION_TAG}"
echo "에셋 디렉토리: ${ASSETS_DIR}"
echo "출력 파일: ${OUTPUT_FILE}"

if [[ -z "$VERSION_TAG" ]]; then
  echo "::error::Version tag (INPUT_VERSION_TAG) is required."
  exit 1
fi

if [ ! -d "$ASSETS_DIR" ]; then
  echo "::error::Asset directory '$ASSETS_DIR' not found."
  # 에셋이 없을 경우 빈 본문 생성 또는 오류 종료 선택 가능
  # 여기서는 빈 플랫폼 목록으로 진행
  mkdir -p "$(dirname "${OUTPUT_FILE}")" # 출력 디렉토리 생성
  echo "## Platform binary release ${VERSION_TAG}" > "${OUTPUT_FILE}"
  echo "" >> "${OUTPUT_FILE}"
  echo "No release assets found in ${ASSETS_DIR}." >> "${OUTPUT_FILE}"
  echo "릴리스 본문 생성 완료 (에셋 없음): ${OUTPUT_FILE}"
  exit 0
fi

# --- 릴리스 본문 내용 생성 ---
# 파일 생성 및 기본 내용 작성
mkdir -p "$(dirname "${OUTPUT_FILE}")" # 출력 디렉토리 생성
cat << EOF > "${OUTPUT_FILE}"
## Platform binary release ${VERSION_TAG}

바이너리는 하나의 zip 파일과 아래의 개별 에셋으로 제공됩니다.

**Included Platforms:**
EOF

# ASSETS_DIR 내의 하위 디렉토리(플랫폼명) 목록을 찾아 목록 생성
# find 사용: -maxdepth 1 로 바로 하위 항목만, -type d 로 디렉토리만, -printf '%f\n' 로 이름만 출력
platform_list=$(find "${ASSETS_DIR}" -maxdepth 1 -mindepth 1 -type d -printf '- %f\n' | sort)

if [ -n "$platform_list" ]; then
  echo "$platform_list" >> "${OUTPUT_FILE}"
else
  echo "- (No platforms found)" >> "${OUTPUT_FILE}"
fi

echo "" >> "${OUTPUT_FILE}" # 마지막 줄바꿈

echo "릴리스 본문 생성 완료: ${OUTPUT_FILE}"
echo "--- 생성된 내용 ---"
cat "${OUTPUT_FILE}"
echo "------------------"
