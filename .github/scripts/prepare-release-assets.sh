#!/bin/bash
# .github/scripts/prepare-release-assets.sh
# 설명: 다운로드된 빌드 아티팩트에서 최종 릴리스 에셋 준비 (플랫폼 정보 포함 파일명으로 통일)

# 오류 발생 시 즉시 종료, 정의되지 않은 변수 사용 시 오류
set -euo pipefail
# 디버깅 필요 시: set -x

# 입력 파라미터 (스크립트 실행 시 전달)
ARTIFACTS_DIR="${1:?오류: 입력 아티팩트 경로가 필요합니다.}" # 첫 번째 인자, 없으면 오류
OUTPUT_DIR="${2:?오류: 출력 에셋 경로가 필요합니다.}"     # 두 번째 인자, 없으면 오류

# 스크립트가 위치한 디렉토리 기준 저장소 루트 경로 계산
REPO_ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
GRADLE_PROPERTIES_PATH="$REPO_ROOT/gradle.properties"

echo "==== 릴리스 에셋 준비 시작 ===="
echo "입력 아티팩트 경로: ${ARTIFACTS_DIR}"
echo "출력 에셋 경로: ${OUTPUT_DIR}"
echo "저장소 루트: ${REPO_ROOT}"
echo "Gradle 속성 파일 경로: ${GRADLE_PROPERTIES_PATH}"

# --- gradle.properties 파일 존재 확인 ---
if [ ! -f "$GRADLE_PROPERTIES_PATH" ]; then
    echo "::error::gradle.properties 파일을 찾을 수 없습니다 (${GRADLE_PROPERTIES_PATH})."
    exit 1
fi
echo "Gradle 속성 파일 확인 완료."

# --- 바이너리 파일명 추출 (from gradle.properties) ---
echo "바이너리 파일명 추출 중..."
BINARY_FILENAME=$(grep -E '^\s*binaryFilename\s*=' "$GRADLE_PROPERTIES_PATH" | grep -v '^\s*#' | sed -E 's/^\s*binaryFilename\s*=\s*(.*)\s*/\1/' | head -n 1)

if [ -z "$BINARY_FILENAME" ]; then
    echo "::error::gradle.properties 에서 binaryFilename 값을 추출하지 못했습니다."
    exit 1
fi
echo "기준 바이너리 파일명: ${BINARY_FILENAME}"

# --- 출력 디렉토리 준비 ---
echo "출력 디렉토리 정리 및 생성 중: ${OUTPUT_DIR}"
rm -rf "${OUTPUT_DIR}"
mkdir -p "${OUTPUT_DIR}"
echo "출력 디렉토리 준비 완료."

# --- 아티팩트 검색 및 플랫폼별 에셋 복사/이름 변경 ---
echo "아티팩트 검색 및 플랫폼별 에셋 처리 시작..."
shopt -s globstar # ** 패턴 사용 가능하도록 설정

# 아티팩트 디렉토리 존재 확인
if [ ! -d "$ARTIFACTS_DIR" ]; then
    echo "::error::입력 아티팩트 디렉토리(${ARTIFACTS_DIR})를 찾을 수 없습니다."
    exit 1
fi

# releaseShared 디렉토리 검색
found_assets=false
for shared_dir in "${ARTIFACTS_DIR}"/**/releaseShared; do
    if [ ! -d "$shared_dir" ]; then
        continue
    fi

    # 플랫폼 이름 추출 (releaseShared의 부모 디렉토리 이름)
    platform_name=$(basename "$(dirname "$shared_dir")")
    echo "--- 처리 중: 플랫폼 ${platform_name} (${shared_dir}) ---"

    # 플랫폼에 따른 확장자 결정
    ext=""
    case "$platform_name" in
        *linux*|*android*) ext="so";;
        *macos*|*ios*) ext="dylib";;
        *windows*|*mingw*) ext="dll";;
        *)
          echo "  ::warning::알 수 없는 플랫폼 유형(${platform_name})입니다. 확장자를 결정할 수 없습니다."
          continue
          ;;
    esac
    # 플랫폼 정보를 포함한 최종 파일명 (<binaryFilename>-<platform>.<ext>)
    target_filename_with_platform="${BINARY_FILENAME}-${platform_name}.${ext}"
    echo "  결정된 확장자: .${ext}, 목표 파일명: ${target_filename_with_platform}"

    # 해당 releaseShared 디렉토리 내에서 바이너리 파일 검색
    src_file=$(find "$shared_dir" -maxdepth 1 -type f -iname "*${BINARY_FILENAME}*.${ext}" -print -quit)

    if [ -n "$src_file" ] && [ -f "$src_file" ]; then
        echo "  발견된 원본 파일: ${src_file}"
        # 출력 디렉토리에 플랫폼 정보 포함 이름으로 직접 복사
        cp "$src_file" "${OUTPUT_DIR}/${target_filename_with_platform}"
        echo "  복사 및 이름 변경 완료: ${OUTPUT_DIR}/${target_filename_with_platform}"
        found_assets=true
    else
        echo "  ::warning::플랫폼 ${platform_name} 에서 '${BINARY_FILENAME}' 포함 .${ext} 파일을 찾지 못했습니다 (${shared_dir}). 빌드 아티팩트를 확인하세요."
    fi
    echo "--- ${platform_name} 처리 완료 ---"
done

# --- 결과 확인 ---
echo "최종 에셋 구조 확인 (${OUTPUT_DIR}):"
if command -v tree >/dev/null 2>&1; then
    tree "${OUTPUT_DIR}" || echo "tree 명령어 실행 실패 또는 디렉토리 비어있음."
else
    ls -R "${OUTPUT_DIR}" || echo "ls 명령어 실행 실패 또는 디렉토리 비어있음."
fi

# 결과 디렉토리가 비어있는지 최종 확인
if [ "$found_assets" = false ]; then
    echo "::error::최종 출력 디렉토리(${OUTPUT_DIR})에 에셋이 준비되지 않았습니다. 빌드 아티팩트 또는 스크립트 로직을 확인하세요."
    exit 1
fi

echo "==== 릴리스 에셋 준비 완료 ===="
