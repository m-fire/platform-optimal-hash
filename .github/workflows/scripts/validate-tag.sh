#!/bin/bash
# 푸시된 Git 태그와 ./gradle.properties 의 `libVersion` 이 일치하는지 검증

set -e # 오류 발생 시 즉시 종료

# 입력: 푸시된 태그 이름, properties 버전으로 만든 태그 이름 (환경 변수)
TAG_NAME="${INPUT_PUSHED_TAG}"
VERSION_TAG_FROM_PROPS="${INPUT_VERSION_TAG_FROM_PROPS}"
COMMIT_SHA="${INPUT_COMMIT_SHA}"

echo "==== Tag Validation Start ===="
echo "Pushed tag: ${TAG_NAME}"
echo "Version tag from gradle.properties: ${VERSION_TAG_FROM_PROPS}"
echo "Commit SHA: ${COMMIT_SHA}"

if [[ -z "$TAG_NAME" || -z "$VERSION_TAG_FROM_PROPS" ]]; then
  echo "::error::Required environment variables (INPUT_PUSHED_TAG, INPUT_VERSION_TAG_FROM_PROPS) are not set."
  exit 1
fi

if [[ "$TAG_NAME" != "$VERSION_TAG_FROM_PROPS" ]]; then
  echo "::error::Pushed tag ($TAG_NAME) does not match libVersion in gradle.properties ($VERSION_TAG_FROM_PROPS) at commit ${COMMIT_SHA}."
  exit 1
fi

echo "Tag validation successful."
echo "==== Tag Validation End ===="
