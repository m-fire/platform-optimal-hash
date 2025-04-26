#!/bin/bash
# Non-Apple 플랫폼 (Linux, Android, Windows) 릴리스 빌드 수행

set -e # 오류 발생 시 즉시 종료

echo "==== Non-Apple Target Build Start ===="
./gradlew --build-cache \
        :library:linkReleaseSharedLinuxX64 \
        :library:linkReleaseSharedAndroidNativeArm64 \
        :library:linkReleaseSharedAndroidNativeX64 \
        :library:linkReleaseSharedWindowsX64 \
        #:library:linkReleaseSharedMingwX64 \ # 기본 Mingw 테스크
        # 필요시 assembleRelease 등 다른 태스크 사용
echo "==== Non-Apple Target Build End ===="
