#!/bin/bash
# ./bin 디렉토리의 변경사항을 Git에 커밋하고 원격 저장소에 푸시

# 오류 발생 시 스크립트 즉시 종료
set -e

# 입력 변수 (워크플로우에서 환경 변수로 전달받음)
VERSION_TAG="${INPUT_VERSION_TAG}"     # 커밋 메시지에 사용할 버전 태그 (예: v1.0.0)
GIT_USER_NAME="${INPUT_GIT_USER_NAME:-"github-actions[bot]"}" # Git 사용자 이름 (기본값 설정)
GIT_USER_EMAIL="${INPUT_GIT_USER_EMAIL:-"github-actions[bot]@users.noreply.github.com"}" # Git 사용자 이메일 (기본값 설정)
TARGET_BRANCH="$(git rev-parse --abbrev-ref HEAD)" # 푸시 대상 브랜치: 현재 브랜치
COPY_TO_DIR="bin" # 커밋 대상 디렉토리

echo "Git 커밋 및 푸시 시작..."
echo "버전 태그: ${VERSION_TAG}"
echo "대상 디렉토리: ${COPY_TO_DIR}"
echo "대상 브랜치: ${TARGET_BRANCH}"

# 버전 태그 입력 확인
if [ -z "${VERSION_TAG}" ]; then
  echo "오류: 커밋 메시지에 사용할 버전 태그가 필요합니다. (INPUT_VERSION_TAG)"
  exit 1
fi

# Git 사용자 설정
echo "Git 사용자 설정: ${GIT_USER_NAME} <${GIT_USER_EMAIL}>"
git config --global user.name "${GIT_USER_NAME}"
git config --global user.email "${GIT_USER_EMAIL}"

# 변경사항 스테이징
echo "변경사항 스테이징 (${COPY_TO_DIR})..."
# 디렉토리가 존재하지 않을 경우 오류 방지
if [ -d "${COPY_TO_DIR}" ]; then
  git add "${COPY_TO_DIR}"/*
else
  echo "경고: 커밋 대상 디렉토리(${COPY_TO_DIR})가 존재하지 않습니다."
  exit 0 # 변경사항 없으므로 정상 종료
fi


# 변경사항 확인 및 커밋
echo "변경사항 확인..."
if ! git diff --staged --quiet; then
  echo "변경사항 감지됨. 커밋 진행..."
  COMMIT_MESSAGE="Add/Update binaries for release ${VERSION_TAG}"
  git commit -m "${COMMIT_MESSAGE}"
  echo "커밋 완료: ${COMMIT_MESSAGE}"

  # 원격 저장소에 푸시
  echo "원격 저장소(${TARGET_BRANCH} 브랜치)에 푸시 중..."
  # 인증 토큰 명확화 (GITHUB_TOKEN 사용)
  git push https://x-access-token:"${GITHUB_TOKEN}"@github.com/"${GITHUB_REPOSITORY}".git HEAD:"${TARGET_BRANCH}"
  echo "푸시 완료."
else
  echo "변경사항 없음. 커밋 및 푸시 건너뜀."
fi

echo "Git 커밋 및 푸시 완료."
