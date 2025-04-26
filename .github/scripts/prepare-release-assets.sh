#!/bin/bash
# 다운로드된 빌드 아티팩트에서 최종 릴리스 에셋 준비 (가독성 개선)
# 함수 분리를 통해 로직 모듈화 및 가독성 향상

set -e # 오류 발생 시 즉시 종료

# --- Helper Functions ---

# 정보 로그 출력
log_info() {
  echo "INFO: $1"
}

# 경고 로그 출력
log_warn() {
  echo "WARN: $1" >&2 # 표준 오류로 출력
}

# 오류 로그 출력 및 종료
log_error_exit() {
  echo "ERROR: $1" >&2 # 표준 오류로 출력
  exit 1
}

# gradle.properties 에서 binaryFilename 값을 추출하는 함수
get_binary_filename() {
  local props_path="$1"
  local filename_var="binaryFilename" # 찾을 속성 이름

  if [[ ! -f "$props_path" ]]; then
    log_error_exit "gradle.properties 파일을 찾을 수 없습니다 (${props_path})."
  fi

  # 'binaryFilename=' 로 시작하고 주석(#)이 아닌 줄을 찾아 '=' 뒤의 값을 추출
  local filename
  filename=$(grep -E "^\s*${filename_var}\s*=" "$props_path" | grep -v '^\s*#' | sed -E "s/^\s*${filename_var}\s*=\s*(.*)\s*/\1/" | head -n 1)

  if [[ -z "$filename" ]]; then
    log_error_exit "gradle.properties 에서 ${filename_var} 값을 추출하지 못했습니다."
  fi

  echo "$filename" # 추출된 파일명 반환
}

# 플랫폼 이름에 따른 바이너리 확장자를 반환하는 함수
get_platform_extension() {
  local platform_name="$1"
  local ext="so" # 기본값 (Linux, Android, Windows)

  if [[ "${platform_name}" == *"macos"* || "${platform_name}" == *"ios"* ]]; then
      ext="dylib"
  elif [[ "${platform_name}" == *"windows"* || "${platform_name}" == *"mingw"* ]]; then
      ext="dll"
  fi
  echo "$ext" # 결정된 확장자 반환
}

# 특정 플랫폼의 에셋을 처리하는 함수 (소스 파일 검색, 복사, 이름 변경)
process_platform_assets() {
  local shared_dir="$1"       # 예: downloaded-artifacts/artifact-name/linuxX64/releaseShared
  local platform_name="$2"    # 예: linuxX64
  local binary_filename="$3"  # 예: my_library
  local output_base_dir="$4"  # 예: release-assets
  local artifact_name="$5"    # 예: non-apple-binaries (경고 메시지용)

  log_info "  플랫폼 처리 중: ${platform_name} (${shared_dir})"

  local ext
  ext=$(get_platform_extension "$platform_name")
  local target_filename="${binary_filename}.${ext}"
  local platform_output_dir="${output_base_dir}/${platform_name}"

  log_info "    확장자: .${ext}, 목표 파일명: ${target_filename}"

  # 해당 releaseShared 디렉토리 내에서 바이너리 파일 검색
  local src_file
  src_file=$(find "$shared_dir" -maxdepth 1 -type f -iname "*${binary_filename}*.${ext}" -print -quit)

  if [[ -z "$src_file" ]]; then
    log_warn "플랫폼 ${platform_name} (${artifact_name}) 에서 '${binary_filename}' 포함 .${ext} 파일을 찾지 못했습니다 (${shared_dir})."
    return # 파일을 못 찾으면 이 플랫폼 처리는 여기서 종료 (오류는 아님)
  fi

  log_info "    발견된 원본 파일: ${src_file}"

  # 출력 디렉토리에 플랫폼 하위 폴더 생성
  mkdir -p "$platform_output_dir"

  # 대상 경로로 복사 및 이름 변경
  if cp "$src_file" "${platform_output_dir}/${target_filename}"; then
    log_info "    복사 및 이름 변경 완료: ${platform_output_dir}/${target_filename}"
  else
    log_warn "파일 복사 실패: ${src_file} -> ${platform_output_dir}/${target_filename}"
  fi
}


# --- Main Script Logic ---

# 입력 파라미터 처리
ARTIFACTS_BASE_DIR=${1:-"downloaded-artifacts"}
OUTPUT_DIR=${2:-"release-assets"}

REPO_ROOT="$(cd "$(dirname "$0")/../../.." && pwd)" # 스크립트 위치 기준 저장소 루트
GRADLE_PROPERTIES_PATH="$REPO_ROOT/gradle.properties"

log_info "==== 릴리스 에셋 준비 시작 ===="
log_info "입력 아티팩트 기본 경로: ${ARTIFACTS_BASE_DIR}"
log_info "출력 에셋 경로: ${OUTPUT_DIR}"

# 1. 바이너리 파일명 추출
log_info "바이너리 파일명 추출 중 (from ${GRADLE_PROPERTIES_PATH})..."
BINARY_FILENAME=$(get_binary_filename "$GRADLE_PROPERTIES_PATH")
log_info "기준 바이너리 파일명: ${BINARY_FILENAME}"

# 2. 출력 디렉토리 준비
log_info "출력 디렉토리 준비 중 (${OUTPUT_DIR})..."
rm -rf "${OUTPUT_DIR}"
mkdir -p "${OUTPUT_DIR}"
log_info "출력 디렉토리 생성 완료: ${OUTPUT_DIR}"

# 3. 아티팩트 검색 및 플랫폼별 에셋 처리
log_info "아티팩트 검색 및 플랫폼별 에셋 처리 시작..."

# 입력 아티팩트 기본 경로 (${ARTIFACTS_BASE_DIR}) 하위의 모든 디렉토리 (아티팩트 이름별 디렉토리) 순회
find "${ARTIFACTS_BASE_DIR}" -mindepth 1 -maxdepth 1 -type d | while IFS= read -r artifact_dir; do
    artifact_name=$(basename "$artifact_dir")
    log_info "--- 아티팩트 처리 중: ${artifact_name} (${artifact_dir}) ---"

    # 각 아티팩트 디렉토리 내에서 'releaseShared' 디렉토리 검색 및 처리
    find "$artifact_dir" -mindepth 2 -type d -name "releaseShared" | while IFS= read -r shared_dir; do
    platform_name=$(basename "$(dirname "$shared_dir")")
        process_platform_assets "$shared_dir" "$platform_name" "$BINARY_FILENAME" "$OUTPUT_DIR" "$artifact_name"
done
    log_info "--- 아티팩트 ${artifact_name} 처리 완료 ---"
done

# 4. 결과 확인
log_info "최종 에셋 구조 (${OUTPUT_DIR}):"
if command -v tree >/dev/null 2>&1; then
    tree "${OUTPUT_DIR}" || log_warn "tree 명령어 실행 실패 또는 디렉토리 비어있음"
else
    ls -R "${OUTPUT_DIR}" || log_warn "ls 명령어 실행 실패 또는 디렉토리 비어있음"
fi

# 결과 디렉토리가 비어있는지 최종 확인 (선택적)
if [[ -z "$(ls -A "${OUTPUT_DIR}")" ]]; then
    log_warn "최종 출력 디렉토리(${OUTPUT_DIR})가 비어 있습니다. 아티팩트 또는 파일 검색 로직을 확인하세요."
fi

log_info "==== 릴리스 에셋 준비 완료 ===="

exit 0 # 성공 종료 명시
