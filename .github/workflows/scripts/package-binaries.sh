#!/bin/bash
# 빌드된 모든 플랫폼 바이너리를 수집하여 GitHub Release용 패키지 생성

set -e  # 오류 발생시 스크립트 종료

# 인자로 전달받은 버전 정보 (미지정시 날짜 기반으로 생성)
VERSION=${1:-$(date +'%Y.%m.%d')}
LIB_DIR=${2:-"library"}
OUTPUT_DIR=${3:-"release-package"}
PKG_NAME="platform-binaries-${VERSION}"

echo "==== 플랫폼 바이너리 패키징 시작 ===="
echo "버전: ${VERSION}"
echo "라이브러리 경로: ${LIB_DIR}"
echo "출력 경로: ${OUTPUT_DIR}"

# 출력 디렉토리 생성
mkdir -p "${OUTPUT_DIR}"
rm -rf "${OUTPUT_DIR}"  # 기존 파일 제거

# 변수명 통일 및 라이브러리 파일명 추출 예외 처리
LIB_NAME=$(grep "val libraryFilename" "${LIB_DIR}/build.gradle.kts" | sed -E 's/.*val libraryFilename\s*=\s*"([^"]+)".*/\1/')
if [ -z "$LIB_NAME" ]; then
  echo "경고: 라이브러리 파일명을 추출하지 못했습니다. 기본값 사용: platform_lib"
  LIB_NAME="platform_lib"
fi

echo "라이브러리 파일명: ${LIB_NAME}"

# 빌드 디렉토리
BUILD_BIN_DIR="${LIB_DIR}/build/bin"

# 모든 플랫폼 디렉토리 찾기
echo "빌드된 플랫폼 검색 중..."
PLATFORMS=$(find "${BUILD_BIN_DIR}" -type d -name "releaseShared" | awk -F/ '{print $(NF-1)}')

# 각 플랫폼 처리
for PLATFORM in ${PLATFORMS}; do
    echo "처리 중: ${PLATFORM}"
    mkdir -p "${OUTPUT_DIR}/${PLATFORM}"
    EXT="so"
    if [[ "${PLATFORM}" == *"macos"* || "${PLATFORM}" == *"ios"* ]]; then
        EXT="dylib"
    elif [[ "${PLATFORM}" == *"windows"* ]]; then
        EXT="dll"
    fi
    # 확장자 일치 + LIB_NAME 포함 파일 복사
    BIN_DIR="${BUILD_BIN_DIR}/${PLATFORM}/releaseShared"
    found=0
    for src in "${BIN_DIR}"/*."${EXT}"; do
        fname=$(basename "$src")
        if [[ -f "$src" && "$fname" == *"${LIB_NAME}"* ]]; then
            cp -v "$src" "${OUTPUT_DIR}/${PLATFORM}/${LIB_NAME}.${EXT}"
            echo "복사 완료: $src -> ${OUTPUT_DIR}/${PLATFORM}/${LIB_NAME}.${EXT}"
            found=1
            break
        fi
    done
    if [[ $found -eq 0 ]]; then
        echo "경고: ${BIN_DIR} 내에 확장자 ${EXT} 및 LIB_NAME(${LIB_NAME})이 포함된 파일이 없습니다."
    fi
done

# 메타데이터 파일 생성
cat > "${OUTPUT_DIR}/metadata.json" << EOF
{
  "name": "${LIB_NAME}",
  "version": "${VERSION}",
  "buildDate": "$(date +'%Y-%m-%d %H:%M:%S')",
  "platforms": [$(echo "${PLATFORMS}" | sed 's/ /", "/g; s/^/"/; s/$/"/')]
}
EOF

# 압축 파일 생성
echo "압축 파일 생성 중..."
CURRENT_DIR=$(pwd)
cd "${OUTPUT_DIR}" || exit
zip -r "../${PKG_NAME}.zip" ./*
cd "${CURRENT_DIR}" || exit

echo "==== 패키징 완료 ===="
echo "생성된 파일: ${PKG_NAME}.zip"
