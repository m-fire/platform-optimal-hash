## 워크플로우 분리 개요 및 요약

### 1. PR 검증 워크플로우 (`pr-validation.yml`)

* **주제:** Pull Request 코드 검증
    * **Job: `validate-code` (코드 품질 및 버전 검증)**
        * 단계: 기본 환경 설정 (코드 체크아웃, Java/Gradle 설정, 스크립트 권한 부여)
        * 단계: 코드 검사 및 린터 실행 (Composite Action)
        * 단계: 최신 릴리스 태그 가져오기
        * 단계: 버전 증가 유효성 검증 (스크립트)
* **세부 절차 요약:**
    1. `main` 브랜치로 향하는 Pull Request 생성/업데이트 시 트리거됨.
    2. **기본 환경 설정:** 코드 체크아웃, Java 17/Gradle 환경 설정(캐싱 활성화), 스크립트 실행 권한 부여 진행.
    3. **코드 검사:** Gradle `check`, `ktlintCheck` 실행으로 코드 품질 및 스타일 검증 (`run-checks` Composite Action).
    4. **버전 증가 검증:** `gradle.properties`의 `libVersion` 값을 가져와 앞뒤 공백을 제거(trim)하고, 가장 최근 시맨틱 버전 태그 조회 후 trim된 `libVersion`
       이 이보다 높은 버전인지 검증 (`validate-pr-version.sh`).
    5. 모든 단계 성공 시 PR에 녹색 체크 표시, 실패 시 빨간 X 표시.

### 2. 릴리스 워크플로우 (`release.yml`)

* **주제:** 태그 기반 빌드 및 릴리스
    * **Job: `validate-release-version` (릴리스 버전 검증)**
        * 단계: 기본 환경 설정
        * 단계: 태그 버전 일치 검증 (스크립트)
    * **Job: `build-non-apple` (Non-Apple 플랫폼 빌드)**
        * 단계: 기본 환경 설정
        * 단계: Non-Apple 대상 빌드 (Linux, Android, Windows)
        * 단계: Non-Apple 빌드 아티팩트 업로드
    * **Job: `build-apple` (Apple 플랫폼 빌드)**
        * 단계: 기본 환경 설정
        * 단계: Xcode 설정
        * 단계: Apple 대상 빌드 (macOS, iOS)
        * 단계: Apple 빌드 아티팩트 업로드
    * **Job: `package-release` (패키징 및 릴리스 생성)**
        * 단계: 기본 환경 설정
        * 단계: 버전 정보 결정 (스크립트)
        * 단계: 모든 빌드 아티팩트 다운로드 (플랫폼별 빌드 결과 취합)
        * 단계: 릴리스 에셋 준비 (스크립트 - 플랫폼 포함 파일명으로 통일)
        * 단계: Zip 아카이브 생성 (배포용 단일 압축 파일 생성)
        * 단계: GitHub 릴리스 생성 및 에셋 업로드 (최종 릴리스 발행)
* **세부 절차 요약:**
    1. `v*` 태그 푸시 또는 수동 실행 시 트리거됨.
    2. **버전 검증 (`validate-release-version` Job):** 기본 환경 설정 후, `gradle.properties`의 `libVersion` 값을 trim하여 푸시된 태그 이름과
       일치하는지 검증 (`validate-tag-version.sh`). 불일치 시 워크플로우 중단.
    3. **플랫폼별 빌드 (`build-non-apple`, `build-apple` Jobs - 병렬 실행):** 버전 검증 성공 시, 각 플랫폼 환경에서 코드 빌드 후 결과물(공유 라이브러리 등)을
       아티팩트로 업로드.
    4. **패키징 및 릴리스 (`package-release` Job):**

    * 모든 빌드 Job 성공 시 실행됨.
    * 기본 환경 설정 후, `gradle.properties`에서 최종 버전 정보 읽기 (`get-version-from-gradle.sh`).
    * **아티팩트 다운로드:** 이전 빌드 Job들에서 업로드한 Non-Apple 및 Apple 빌드 결과물(아티팩트)을 하나의 작업 공간으로 다운로드하여 취합.
    * **릴리스 에셋 준비:** 다운로드한 아티팩트들을 `release-assets` 폴더에 저장하되, 각 바이너리 파일명에 플랫폼 정보를 포함하여 고유하게 만듦 (예:
      `my-library-linuxX64.so`, `my-library-macosArm64.dylib`) (`prepare-release-assets.sh`). 이는 GitHub 릴리스 에셋 이름 충돌을
      방지하고 플랫폼별 다운로드를 가능하게 함.
    * **Zip 아카이브 생성:** `release-assets` 폴더에 준비된 모든 플랫폼별 바이너리를 포함하는 단일 Zip 압축 파일 생성 (예: `platform-binaries-1.0.0.zip`).
    * **GitHub 릴리스 발행:** 워크플로우를 트리거한 태그 이름으로 GitHub에 새로운 릴리스 생성. 생성된 Zip 파일과 `release-assets` 폴더 내의 플랫폼 정보가 포함된 개별 바이너리
      파일들을 이 릴리스에 에셋으로 업로드. 릴리스 노트는 GitHub 자동 생성 기능 활용.
