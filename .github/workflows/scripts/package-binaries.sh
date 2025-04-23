#!/bin/bash
# 빌드된 모든 플랫폼 바이너리를 수집하여 GitHub Release용 패키지 생성

set -e  # 오류 발생시 스크립트 종료

# 인자로 전달받은 버전 정보 (미지정시 날짜 기반으로 생성)
VERSION=${1:-$(date +'%Y.%m.%d')}
LIB_DIR=${2:-"library"}
OUTPUT_DIR=${3:-"release-package"}
PKG_NAME="platform-binaries-${VERSION}"

REPO_ROOT="$(cd "$(dirname "$0")/../../.." && pwd)"
LIB_PATH="$REPO_ROOT/$LIB_DIR"
OUTPUT_PATH="$REPO_ROOT/$OUTPUT_DIR"

cd "$REPO_ROOT"

echo "==== 플랫폼 바이너리 패키징 시작 ===="
echo "버전: ${VERSION}"
echo "라이브러리 경로: ${LIB_PATH}"
echo "출력 경로: ${OUTPUT_PATH}"

# 출력 디렉토리 생성
mkdir -p "${OUTPUT_PATH}"
rm -rf "${OUTPUT_PATH}"  # 기존 파일 제거

# 변수명 통일 및 라이브러리 파일명 추출 예외 처리
LIB_NAME=$(grep "val libraryFilename" "${LIB_PATH}/build.gradle.kts" | sed -E 's/.*val libraryFilename\s*=\s*"([^"]+)".*/\1/')
if [ -z "$LIB_NAME" ]; then
  echo "경고: 라이브러리 파일명을 추출하지 못했습니다. 기본값 사용: platform_lib"
  LIB_NAME="platform_lib"
fi

echo "라이브러리 파일명: ${LIB_NAME}"

# 빌드 디렉토리
BUILD_BIN_DIR="${LIB_PATH}/build/bin"

# 모든 플랫폼 디렉토리 찾기
echo "빌드된 플랫폼 검색 중..."
PLATFORMS=$(find "${BUILD_BIN_DIR}" -type d -name "releaseShared" | awk -F/ '{print $(NF-1)}')

# 각 플랫폼 처리
for PLATFORM in ${PLATFORMS}; do
    echo "처리 중: ${PLATFORM}"
    mkdir -p "${OUTPUT_PATH}/${PLATFORM}"
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
        if [[ -f "$src" && "$src" == *"${LIB_NAME}"* ]]; then
            cp "$src" "${OUTPUT_PATH}/${PLATFORM}/"
            found=1
        fi
    done
    if [ $found -eq 0 ]; then
        echo "경고: ${PLATFORM} 플랫폼의 바이너리를 찾지 못했습니다."
    fi
    # (추가 로직 필요시 여기에)
done

echo "==== 바이너리 패키징 완료 ===="

# zip 파일을 저장소 루트에 생성
cd "$REPO_ROOT"
zip -r "platform-binaries-${VERSION}.zip" "$OUTPUT_PATH"
