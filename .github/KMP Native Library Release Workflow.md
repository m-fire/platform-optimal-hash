# KMP 네이티브 라이브러리 워크플로우

이 문서는 Kotlin Multiplatform (KMP) 네이티브 라이브러리의 Pull Request 검증 및 릴리즈 자동화를 위한 GitHub Actions 워크플로우를 설명함. 워크플로우는 복합 액션(
Composite Actions)을 활용하여 재사용성과 유지보수성을 높임.

## 워크플로우 종류

1. **PR Check (pr-check.yml)**: Pull Request가 생성되거나 업데이트될 때 실행되어 코드 품질과 빌드 가능성을 검증함.
2. **버전 검증 및 업데이트 (validate-and-update-version.yml)**: 수동(workflow\_dispatch)으로 트리거되어 릴리즈 버전을 검증하고, 필요한 경우 main 브랜치의
   gradle.properties 파일을 자동으로 업데이트 및 커밋함.
3. **태그 기반 릴리즈 (release-on-tag.yml)**: v\* 형태의 태그가 푸시될 때 자동으로 트리거되어, 해당 버전의 라이브러리 빌드, 패키징, GitHub 릴리즈 생성을 수행함.

## 1. PR Check 워크플로우 (pr-check.yml)

이 워크플로우는 PR 변경 사항이 코드베이스의 안정성을 해치지 않는지 확인하는 것을 목표로 함.

**트리거:**

* main 브랜치 대상 Pull Request (on: pull\_request)
* 특정 경로 변경 시 (paths)
* 수동 실행 (on: workflow\_dispatch)

**Jobs:**

1. **validate (Lint and Test (Gradle))**: 기본적인 코드 정적 분석, 린팅, 단위 테스트 수행 (Ubuntu).
2. **test-gh-scripts (Test GitHub Scripts (Python))**: 워크플로우 헬퍼 Python 스크립트들의 단위 테스트 수행 (Ubuntu).
3. **test-build-apple (Test Build (Apple Targets))**: 주요 Apple 플랫폼 타겟 빌드 가능성 검증 (macOS).

**특징:**

* Job 간 명확한 책임 분담 및 needs를 통한 순차 실행.
* 테스트 실패 시 자동 중단.
* 환경 설정은 복합 액션(setup-environment)으로 재사용.

## 2. 버전 검증 및 업데이트 워크플로우 (validate-and-update-version.yml)

이 워크플로우는 릴리즈 시작 전 버전을 검증하고 gradle.properties 파일을 준비하는 역할을 함.

**트리거:**

* 수동 실행 (on: workflow\_dispatch)
  * **입력:** version (릴리즈할 버전. 예: 1.1.0, 1.2.0-rc1)

**Job: validate-and-update**

* **실행 환경:** Ubuntu (runs-on: ubuntu-latest)
* **권한:** contents: write (파일 수정 및 커밋 위해)
* **역할:**
  1. main 브랜치 체크아웃.
  2. 입력된 version 유효성 검증:

  * gradle.properties의 libVersion보다 크거나 같은지 확인.
  * 저장소의 최신 Git 태그 버전보다 크거나 같은지 확인 (태그 존재 시).

  3. 검증 통과 시, 입력 version이 libVersion보다 크면 gradle.properties 파일 수정.
  4. 수정된 경우, "Release Bot" 이름으로 main 브랜치에 변경 사항 커밋 및 푸시 (git-auto-commit-action 사용).
* **주요 단계:**
  * 코드 체크아웃 (actions/checkout@v4 with ref: 'main', fetch-depth: 0).
  * Python 환경 설정 및 packaging 라이브러리 설치 (actions/setup-python@v5).
  * 버전 검증 및 업데이트 스크립트 실행 (validate\_version\_consistency.py).
  * 조건부 자동 커밋 (stefanzweifel/git-auto-commit-action@v5).
* **주의:** 이 워크플로우는 **실제 라이브러리 빌드나 GitHub 릴리즈 생성 작업을 수행하지 않음.**

## 3. 태그 기반 릴리즈 워크플로우 (release-on-tag.yml)

이 워크플로우는 **개발자가 수동으로 생성하여 푸시한 v\* 태그**에 의해 트리거되어 실제 릴리즈 프로세스를 수행함. (validate-and-update-version.yml 실행 완료 후 진행).

**트리거:**

* v\* 형태의 태그 푸시 (on: push: tags: \['v\*'\])

**Jobs:**

1. **build\_linux\_windows\_android (Build Linux \+ Windows \+ Android)**: Linux, Windows, Android 네이티브 타겟 빌드 및 아티팩트
   업로드 (Ubuntu).
2. **build\_apple (Build macOS \+ iOS)**: macOS, iOS 네이티브 타겟 빌드 및 아티팩트 업로드 (macOS).
3. **create\_release (Create Release Package)**:

* **의존성:** 모든 빌드 Job 성공 후 실행.
* **역할:** 모든 빌드 아티팩트 취합, GitHub Release 생성 및 에셋 업로드.
* **주요 단계:**
  * 태그된 코드 체크아웃.
  * 릴리즈 준비 (복합 액션 .github/actions/prepare-release 사용):
    * 모든 빌드 아티팩트 다운로드.
    * 릴리즈 에셋 정리 (prepare\_release\_assets.py).
    * 릴리즈 본문 및 Zip 아카이브 생성 (generate\_release\_info.py).
  * GitHub 릴리즈 생성 및 에셋 업로드 (softprops/action-gh-release@v2).

**(선택 사항) publish\_maven (Publish to Maven Central)**: Maven Central 배포 (필요 시 활성화).

**특징:**

* **릴리즈 프로세스 분리:** 버전 준비(수동 트리거)와 실제 릴리즈(태그 트리거)를 분리하여 안정성 향상.
* 빌드 작업 병렬 실행 및 플랫폼별 최적 러너 사용.
* 복합 액션(setup-environment, prepare-release, publish-library) 활용으로 워크플로우 간소화.
* 아티팩트 업로드/다운로드를 통한 Job 간 결과물 공유.

## 4. 주요 복합 액션 (Composite Actions)

* **.github/actions/setup-environment**: Java, Python, Xcode 등 개발 환경 설정을 위한 공통 단계 캡슐화.
* **.github/actions/prepare-release**: 빌드 아티팩트 다운로드, 플랫폼별 에셋 정리, 릴리즈 노트 및 Zip 아카이브 생성을 담당.
* **.github/actions/publish-library**: GPG 설정 및 Gradle을 이용한 Maven Central 게시 작업 수행.

## 5. 헬퍼 스크립트 (.github/scripts/)

워크플로우의 특정 작업을 수행하기 위한 Python 스크립트들.

* validate\_version\_consistency.py: 입력 버전, gradle.properties의 libVersion, 최신 Git 태그 비교 검증 및 gradle.properties 자동 업데이트
  수행.
* prepare\_release\_assets.py: 다운로드된 빌드 아티팩트를 플랫폼별 디렉토리 구조로 정리.
* generate\_release\_info.py: 릴리즈 본문(Markdown)과 모든 플랫폼 바이너리를 포함하는 Zip 아카이브 생성.
* test\_\*.py: 각 헬퍼 스크립트에 대한 단위 테스트 (unittest).
