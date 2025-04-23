#!/bin/bash
set -e

# 스크립트 위치 기준으로 경로 보정
dirname=$(cd "$(dirname "$0")/../../.." && pwd)
# 테스트 환경(LIBRARY_FILE) 우선, 아니면 기존 경로
file="${LIBRARY_FILE:-$dirname/platform-optimal-hash/library/build.gradle.kts}"

# 버전 라인 추출 (prerelease 포함)
version_line=$(grep -E 'version\s*=\s*"' "$file")
version=$(echo "$version_line" | grep -oE '[0-9]+(\.[0-9]+)*')
# prerelease 등은 별도 추출
after=$(echo "$version_line" | grep -oE '"[0-9]+(\.[0-9]+)*(-[a-zA-Z0-9.]+)?"' | sed 's/"//g' | grep '-' || true)

# 마지막 자릿수만 증가
dots=$(echo "$version" | grep -o '\.' | wc -l)
new_version=$(echo "$version" | awk -F. '{for(i=1;i<NF;i++) printf $i"."; printf $NF+1}')
if [ -n "$after" ]; then
  new_version="$new_version-$after"
fi
sed -i -E "s/version = \"[0-9]+(\.[0-9]+)*(-[a-zA-Z0-9.]+)?\"/version = \"$new_version\"/" "$file"
echo "Bumped version: $version -> $new_version"
