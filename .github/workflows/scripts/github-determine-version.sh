#!/bin/bash
# 워크플로우 컨텍스트(입력, 태그)를 기반으로 릴리스 버전 결정

# 오류 발생 시 스크립트 즉시 종료
set -e

# 입력 변수 (워크플로우에서 환경 변수로 전달받음)
INPUT_VERSION="${WORKFLOW_INPUT_VERSION}" # github.event.inputs.version
GITHUB_REF="${WORKFLOW_GITHUB_REF}"       # github.ref

VERSION_NUM=""
VERSION_TAG=""

echo "버전 결정 시작..."
echo "입력 버전: ${INPUT_VERSION}"
echo "GitHub Ref: ${GITHUB_REF}"

# 우선순위: 1) 워크플로우 수동 입력 2) Git 태그
if [ -n "${INPUT_VERSION}" ]; then
  echo "수동 입력된 버전 사용: ${INPUT_VERSION}"
  VERSION_NUM="${INPUT_VERSION}"
elif [[ "${GITHUB_REF}" == refs/tags/v* ]]; then
  # refs/tags/v 접두사 제거
  VERSION_NUM="${GITHUB_REF#refs/tags/v}"
  echo "Git 태그에서 버전 추출: ${VERSION_NUM}"
else
  echo "오류: 릴리스 버전을 결정할 수 없습니다."
  echo "태그(v*) 푸시 또는 수동 실행 시 버전 입력이 필요합니다."
  exit 1
fi

# 버전 번호 유효성 검사 (간단한 형태 확인)
if ! [[ "${VERSION_NUM}" =~ ^[0-9]+(\.[0-9]+){0,2}(-[a-zA-Z0-9.]+)?$ ]]; then
 echo "오류: 유효하지 않은 버전 형식입니다: ${VERSION_NUM}"
 exit 1
fi

# 최종 버전 태그 (v 접두사 포함)
VERSION_TAG="v${VERSION_NUM}"

echo "결정된 버전 번호: ${VERSION_NUM}"
echo "결정된 버전 태그: ${VERSION_TAG}"

# 워크플로우에서 사용할 수 있도록 출력 설정
# 최신 output 방식 사용 (테스트 환경에서는 $GITHUB_OUTPUT 미설정)
if [ -n "$GITHUB_OUTPUT" ]; then
  echo "version_num=${VERSION_NUM}" >> "$GITHUB_OUTPUT"
  echo "version_tag=${VERSION_TAG}" >> "$GITHUB_OUTPUT"
fi

echo "버전 결정 완료."
