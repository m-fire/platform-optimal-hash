#!/bin/bash
# 빌드된 모든 플랫폼 바이너리를 수집하여 GitHub Release용 패키지 생성
# gradle.properties 에서 binaryFilename 값을 읽어 최종 파일명으로 사용

set -e  # 오류 발생시 스크립트 종료

# --- 설정값 ---
VERSION=${1:-$(date +'%Y.%m.%d')}
LIB_DIR=${2:-"library"} # 라이브러리 모듈 경로
OUTPUT_DIR=${3:-"bin"}   # 최종 바이너리 저장 디렉토리 (저장소 루트 기준)
PKG_NAME="platform-binaries-${VERSION}"

# --- 경로 계산 ---
REPO_ROOT="$(cd "$(dirname "$0")/../../.." && pwd)" # 스크립트 위치 기준 저장소 루트
LIB_PATH="$REPO_ROOT/$LIB_DIR"
OUTPUT_PATH="$REPO_ROOT/$OUTPUT_DIR"
BUILD_BIN_DIR="${LIB_PATH}/build/bin" # Gradle 빌드 출력 바이너리 경로

# --- 스크립트 시작 ---
cd "$REPO_ROOT"

echo "==== 플랫폼 바이너리 패키징 시작 ===="
echo "버전: ${VERSION}"
echo "라이브러리 경로: ${LIB_PATH}"
echo "빌드 바이너리 경로: ${BUILD_BIN_DIR}"
echo "최종 출력 경로: ${OUTPUT_PATH}"

# --- 출력 디렉토리 준비 ---
echo "출력 디렉토리 준비 중: ${OUTPUT_PATH}"
mkdir -p "${OUTPUT_PATH}"
if [ -d "${OUTPUT_PATH}" ]; then
  echo "기존 내용 삭제 중..."
  rm -rf "${OUTPUT_PATH:?}/"* # 내용물만 안전하게 삭제
else
    echo "출력 디렉토리가 존재하지 않아 새로 생성합니다."
fi

# --- 바이너리 파일명 추출 (from gradle.properties) ---
GRADLE_PROPERTIES_PATH="$REPO_ROOT/gradle.properties"
echo "바이너리 파일명 추출 중 (from ${GRADLE_PROPERTIES_PATH})..."
BINARY_FILENAME="" # 변수 초기화

if [ ! -f "$GRADLE_PROPERTIES_PATH" ]; then
    echo "경고: gradle.properties 파일을 찾을 수 없습니다 (${GRADLE_PROPERTIES_PATH})." >&2
else
    # 'binaryFilename=' 로 시작하고 주석(#)이 아닌 줄을 찾아 '=' 뒤의 값을 추출
    BINARY_FILENAME=$(grep -E '^\s*binaryFilename\s*=' "$GRADLE_PROPERTIES_PATH" | grep -v '^\s*#' | sed -E 's/^\s*binaryFilename\s*=\s*(.*)\s*/\1/' | head -n 1)
fi

# 추출 실패 시 기본값 사용 또는 오류 처리
if [ -z "$BINARY_FILENAME" ]; then
  echo "경고: gradle.properties 에서 binaryFilename 값을 추출하지 못했습니다." >&2
  # 필요시 기본값 설정 또는 오류 종료
  echo "경고: 기본 바이너리 파일명 사용: default_binary"
  BINARY_FILENAME="default_binary"
  # 또는 오류 종료:
  # echo "오류: gradle.properties 파일에 'binaryFilename=your_name' 설정이 필요합니다." >&2
  # exit 1
fi
echo "바이너리 파일명 결정: ${BINARY_FILENAME}"

# --- 빌드 바이너리 디렉토리 확인 ---
if [ ! -d "$BUILD_BIN_DIR" ]; then
  echo "오류: 빌드 바이너리 디렉토리 '$BUILD_BIN_DIR' 를 찾을 수 없습니다." >&2
  echo "Gradle 빌드가 먼저 성공적으로 완료되었는지 확인하세요." >&2
  exit 1
fi

# 빌드 디렉토리 구조 출력 (디버깅 목적)
echo "--- 빌드 바이너리 디렉토리 구조 (일부) ---"
if command -v tree >/dev/null 2>&1; then
  tree -L 3 "$BUILD_BIN_DIR" || echo "tree 명령어 실행 실패"
else
  find "$BUILD_BIN_DIR" -maxdepth 3 || echo "find 명령어 실행 실패"
fi
echo "------------------------------------------"

# --- 플랫폼별 바이너리 탐색 및 복사 ---
echo "빌드된 플랫폼 검색 및 처리 시작..."
PLATFORMS=$(find "${BUILD_BIN_DIR}" -mindepth 1 -maxdepth 1 -type d -exec test -d '{}/releaseShared' \; -printf '%f\n')

if [ -z "$PLATFORMS" ]; then
    echo "오류: ${BUILD_BIN_DIR} 하위에서 'releaseShared' 디렉토리를 포함하는 플랫폼 디렉토리를 찾을 수 없습니다." >&2
    exit 1
fi

echo "발견된 플랫폼: ${PLATFORMS}"

# 각 플랫폼 처리
for PLATFORM in ${PLATFORMS}; do
    echo "--- 처리 중: ${PLATFORM} ---"
    BIN_DIR="${BUILD_BIN_DIR}/${PLATFORM}/releaseShared" # 실제 바이너리가 있는 경로
    DEST_DIR="${OUTPUT_PATH}/${PLATFORM}" # 최종 복사될 경로
    mkdir -p "${DEST_DIR}" # 플랫폼별 출력 디렉토리 생성

    # 플랫폼에 따른 확장자 결정
    EXT="so" # 기본값 (Linux, Android 등)
    if [[ "${PLATFORM}" == *"macos"* || "${PLATFORM}" == *"ios"* ]]; then
        EXT="dylib"
    elif [[ "${PLATFORM}" == *"windows"* ]]; then
        EXT="dll"
    fi
    echo "사용될 확장자: .${EXT}"

    # 최종 파일명(이름.확장자) 형식 지정
    DEST_FILENAME="${BINARY_FILENAME}.${EXT}"
    echo "대상 파일명 (고정): ${DEST_FILENAME}"

    found=0 # 파일 찾기 플래그

    echo "바이너리 검색 위치: ${BIN_DIR}"

    # 해당 확장자를 가진 파일들을 찾아서 처리
    find "${BIN_DIR}" -maxdepth 1 -type f -name "*.${EXT}" | while IFS= read -r src_file; do
        filename=$(basename "$src_file")

        # 파일명에 BINARY_FILENAME 이 포함되어 있는지 확인 ('lib' 접두사 유무 관계 없음)
        if [[ "$filename" == *"${BINARY_FILENAME}"* ]]; then
            echo "발견된 바이너리: ${filename}"
            # 찾은 파일을 DEST_FILENAME 으로 복사 (이름 변경 효과)
            cp "$src_file" "${DEST_DIR}/${DEST_FILENAME}"
            echo "복사 완료: ${DEST_DIR}/${DEST_FILENAME}"
            found=1
            break # 해당 플랫폼/아키텍처에 대해 하나의 파일만 복사 가정
        else
            echo "파일명 불일치 (무시): ${filename} (BINARY_FILENAME '${BINARY_FILENAME}' 미포함)"
        fi
    done

    # 파일 찾기 결과 확인
    if [ $found -eq 0 ]; then
        echo "경고: ${PLATFORM} 플랫폼 (${BIN_DIR}) 에서 '${BINARY_FILENAME}' 을(를) 포함하고 확장자가 '.${EXT}' 인 바이너리를 찾지 못했습니다."
    fi
    echo "--- ${PLATFORM} 처리 완료 ---"
done

echo "==== 플랫폼별 바이너리 처리 완료 ===="

# --- 최종 zip 파일 생성 ---
cd "$REPO_ROOT" # zip 명령 실행 위치 (저장소 루트)
ZIP_FILENAME="${PKG_NAME}.zip"
echo "최종 zip 파일 생성 중: ${ZIP_FILENAME} (내용: ${OUTPUT_DIR}/)"
zip -r "${ZIP_FILENAME}" "${OUTPUT_DIR}"

echo "==== 패키징 완료: ${ZIP_FILENAME} 파일 생성됨 ===="
