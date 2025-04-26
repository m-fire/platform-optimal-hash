#!/bin/bash
# 다운로드된 빌드 아티팩트에서 최종 릴리스 에셋 준비
# 플랫폼별 폴더 구조를 유지하고 파일명을 binaryFilename 기준으로 통일

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
    # 'binaryFilename=' 로 시작하고 주석(#)이 아닌 줄을 찾아 '=' 뒤의 값을 추출
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

# --- 아티팩트 검색 및 플랫폼별 폴더 구조로 복사/이름 변경 ---
echo "아티팩트 검색 및 플랫폼별 에셋 복사/이름 변경 시작..."

# downloaded-artifacts 하위의 모든 플랫폼별 releaseShared 디렉토리 검색
# find의 `-mindepth 2`옵션은 {downloaded-artifacts}/{artifact-name}/{platform}/releaseShared 구조를 가정
# 만약 downloaded-artifacts/platform/releaseShared 구조라면 -mindepth 1 사용
# 여기서는 이전 단계에서 아티팩트 다운로드 시 path 를 지정하지 않아
# {downloaded-artifacts}/{non-apple-binaries}/{non-apple-platform}/releaseShared 같은 구조로 가정하고 진행
find "${ARTIFACTS_DIR}" -mindepth 2 -type d -name "releaseShared" | while IFS= read -r shared_dir; do
    # 플랫폼 이름 추출 (예: linuxX64, macosArm64)
    platform_name=$(basename "$(dirname "$shared_dir")")
    echo "--- 처리 중: 플랫폼 ${platform_name} (${shared_dir}) ---"

    # 플랫폼에 따른 확장자 결정
    ext="so" # 기본값 (Linux, Android, Windows)
    if [[ "${platform_name}" == *"macos"* || "${platform_name}" == *"ios"* ]]; then
        ext="dylib"
    elif [[ "${platform_name}" == *"windows"* || "${platform_name}" == *"mingw"* ]]; then
        ext="dll"
    fi
    # 최종 파일명 (<binaryFilename>.<ext>)
    target_filename="${BINARY_FILENAME}.${ext}"
    echo "  확장자: .${ext}, 목표 파일명: ${target_filename}"

    # 해당 releaseShared 디렉토리 내에서 바이너리 파일 검색 (하나만 찾는다고 가정)
    # 이름에 BINARY_FILENAME 포함, 올바른 확장자, 파일 타입 (-type f)
    src_file=$(find "$shared_dir" -maxdepth 1 -type f -iname "*${BINARY_FILENAME}*.${ext}" -print -quit)

    if [ -n "$src_file" ]; then
        echo "  발견된 원본 파일: ${src_file}"
        # 출력 디렉토리에 플랫폼 하위 폴더 생성
        platform_output_dir="${OUTPUT_DIR}/${platform_name}"
        mkdir -p "${platform_output_dir}"
        # 대상 경로로 복사 및 이름 변경
        cp "$src_file" "${platform_output_dir}/${target_filename}"
        echo "  복사 및 이름 변경 완료: ${platform_output_dir}/${target_filename}"
    else
        echo "  경고: 플랫폼 ${platform_name} 에서 '${BINARY_FILENAME}' 포함 .${ext} 파일을 찾지 못했습니다 (${shared_dir})."
    fi
    echo "--- ${platform_name} 처리 완료 ---"
done

# --- 결과 확인 ---
echo "최종 에셋 구조 (${OUTPUT_DIR}):"
if command -v tree >/dev/null 2>&1; then
    tree "${OUTPUT_DIR}" || echo "tree 명령어 실행 실패 또는 디렉토리 비어있음"
else
    ls -R "${OUTPUT_DIR}" || echo "ls 명령어 실행 실패 또는 디렉토리 비어있음"
fi

# 결과 디렉토리가 비어있는지 최종 확인 (선택적)
if [ -z "$(ls -A "${OUTPUT_DIR}")" ]; then
    echo "경고: 최종 출력 디렉토리(${OUTPUT_DIR})가 비어 있습니다. 아티팩트 또는 파일 검색 로직을 확인하세요."
fi

echo "==== 릴리스 에셋 준비 완료 ===="
