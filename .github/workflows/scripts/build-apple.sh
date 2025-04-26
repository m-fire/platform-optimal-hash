#!/bin/bash
# Non-Apple 플랫폼 (Linux, Android, Windows) 릴리스 빌드 수행

set -e # 오류 발생 시 즉시 종료

echo "==== Non-Apple Target Build Start ===="
./gradlew --build-cache \
        :library:linkReleaseSharedMacosArm64 \
        :library:linkReleaseSharedMacosX64 \
        :library:linkReleaseSharedIosArm64 \
        :library:linkReleaseSharedIosX64 \
        #:library:linkReleaseSharedIosSimulatorArm64 # 필요 시 추가
echo "==== Non-Apple Target Build End ===="
