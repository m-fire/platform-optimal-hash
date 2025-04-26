#!/bin/bash
# release-assets 디렉토리 내용을 Zip 아카이브로 생성

set -e # 오류 발생 시 즉시 종료

# 입력: 버전 번호, 출력 디렉토리, 아티팩트 디렉토리 (환경 변수 또는 인자)
VERSION_NUM="${INPUT_VERSION_NUM}"
OUTPUT_DIR="." # 현재 작업 디렉토리에 zip 생성
ASSETS_DIR="release-assets"

echo "==== Zip Archive Creation Start ===="
echo "Version Number: ${VERSION_NUM}"
echo "Asset Directory: ${ASSETS_DIR}"
echo "Output Directory: ${OUTPUT_DIR}"

if [[ -z "$VERSION_NUM" ]]; then
  echo "::error::Version number (INPUT_VERSION_NUM) is required."
  exit 1
fi

if [ ! -d "$ASSETS_DIR" ]; then
  echo "::error::Asset directory '$ASSETS_DIR' not found."
  exit 1
fi

PKG_NAME="platform-binaries-${VERSION_NUM}"
ZIP_FILENAME="${OUTPUT_DIR}/${PKG_NAME}.zip" # 경로 포함하여 지정

# release-assets 디렉토리로 이동하지 않고 압축 (경로 문제 방지)
# zip -r <대상 zip 파일> <압축할 대상 폴더>
# -j 옵션: 디렉토리 구조 무시하고 파일만 압축 (사용 안 함)
zip -r "${ZIP_FILENAME}" "${ASSETS_DIR}"

if [ $? -ne 0 ]; then
  echo "::error::Failed to create zip file."
  exit 1
fi

echo "Zip file created: ${ZIP_FILENAME}"

# 워크플로우에서 사용할 수 있도록 출력 설정
if [ -n "$GITHUB_OUTPUT" ]; then
  echo "zip_name=${ZIP_FILENAME}" >> "$GITHUB_OUTPUT"
else
  echo "경고: GITHUB_OUTPUT 환경 변수가 설정되지 않아 출력을 설정할 수 없습니다."
fi

echo "==== Zip Archive Creation End ===="
