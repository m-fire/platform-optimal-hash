# .github/scripts/prepare_release_assets.py
import os
import shutil
import sys
from pathlib import Path

# 필수적으로 포함되어야 할 플랫폼 타겟 목록 정의 (모듈 레벨로 이동)
# TODO: 프로젝트에서 릴리즈 시 필수로 포함해야 하는 모든 플랫폼 타겟을 이 목록에 명시하세요.
required_platforms = {
    "linuxX64",
    "windowsX64",
    "androidNativeArm64",
    "androidNativeX64",
    "macosArm64",
    "macosX64",
    "iosArm64",
    "iosX64",
}

# 플랫폼명 매핑 (모듈 레벨로 이동)
# 예: linuxX64 -> linux, macosX64 -> macos-x64
# TODO: 프로젝트에서 빌드하는 모든 플랫폼 타겟이 이 맵에 포함되어 있고,
# 원하는 출력 디렉토리 이름으로 매핑되어 있는지 확인하세요.
platform_name_map = {
    "linuxX64": "linux",
    "windowsX64": "windows",
    "androidNativeArm64": "android-arm64",
    "androidNativeX64": "android-x64",
    "macosArm64": "macos-arm64",
    "macosX64": "macos-x64",
    "iosArm64": "ios-arm64",
    "iosX64": "ios-x64",
    # 필요한 다른 타겟 추가
}


def get_gradle_property(prop_file_path, key):
    """gradle.properties 파일에서 지정된 키의 값을 읽음."""
    if not prop_file_path.is_file():
        print(f"::error::Gradle properties file not found: {prop_file_path}")
        return None

    try:
        with open(prop_file_path, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith('#') or line.startswith('!'):
                    continue
                # 공백을 허용하며 '=' 기준으로 분리
                parts = line.split('=', 1)
                if len(parts) == 2:
                    k, v = parts[0].strip(), parts[1].strip()
                    if k == key:
                        print(f"::info::Found '{key}' in {prop_file_path}: {v}")
                        return v
    except Exception as e:
        print(f"::error::Error reading {prop_file_path}: {e}")
        return None

    print(f"::error::Key '{key}' not found in {prop_file_path}.")
    return None


def prepare_assets(input_dir_str, output_dir_str, prop_file_str):
    """
    다운로드된 아티팩트에서 릴리스 에셋을 준비합니다.
    input_dir: 다운로드된 아티팩트 루트 디렉토리 (예: downloaded-artifacts)
               actions/download-artifact@v4는 아티팩트 이름으로 하위 디렉토리를 생성합니다.
               예: downloaded-artifacts/non-apple-binaries/...
    output_dir: 준비된 에셋을 저장할 디렉토리 (예: release-assets)
    prop_file: gradle.properties 파일 경로
    """
    input_dir = Path(input_dir_str)
    output_dir = Path(output_dir_str)
    prop_file = Path(prop_file_str)

    # 1. gradle.properties에서 바이너리 파일 이름 가져오기
    binary_filename_base = get_gradle_property(prop_file, 'binaryFilename')
    if binary_filename_base is None:
        print("::error::Could not get 'binaryFilename' from gradle.properties.")
        return False

    # 2. 입력 디렉토리 확인
    if not input_dir.is_dir():
        print(f"::error::Input directory not found: {input_dir}")
        return False

    # 3. 출력 디렉토리 초기화 (기존 내용 삭제 후 재생성)
    if output_dir.exists():
        print(f"::info::Clearing existing output directory: {output_dir}")
        shutil.rmtree(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    print(f"::info::Created output directory: {output_dir}")

    # 4. 아티팩트 디렉토리 탐색 및 바이너리 복사
    found_platforms = set() # 바이너리를 찾은 플랫폼 타겟 목록

    # 예상되는 아티팩트 이름 목록
    artifact_names = ["non-apple-binaries", "apple-binaries"]

    for artifact_name in artifact_names:
        artifact_root_dir = input_dir / artifact_name
        if not artifact_root_dir.is_dir():
            print(f"::warning::Artifact directory not found: {artifact_root_dir}. Skipping.")
            continue

        # 예상되는 빌드 경로 패턴 탐색
        search_pattern = f"library/build/bin/*/releaseShared/{binary_filename_base}.*"
        print(f"::info::Searching for pattern '{search_pattern}' in '{artifact_root_dir}'")

        for binary_file_path in artifact_root_dir.glob(search_pattern):
            if binary_file_path.is_file():
                print(f"::info::Found binary file: {binary_file_path}")

                try:
                    base_path_for_relative = artifact_root_dir / "library" / "build" / "bin"
                    if not base_path_for_relative.is_dir():
                         print(f"::warning::Base path for relative calculation not found: {base_path_for_relative}. Skipping file: {binary_file_path}")
                         continue

                    relative_path = binary_file_path.relative_to(base_path_for_relative)
                    platform_target_name = relative_path.parts[0]

                    # 찾은 플랫폼 타겟을 found_platforms 집합에 추가
                    found_platforms.add(platform_target_name)

                    # 플랫폼명 매핑 (모듈 레벨 변수 사용)
                    friendly_platform_name = platform_name_map.get(platform_target_name, platform_target_name)
                    if platform_target_name not in platform_name_map:
                         print(f"::warning::No specific mapping found for platform target '{platform_target_name}'. Using original name.")

                    # 출력 경로 생성 및 파일 복사
                    dest_dir = output_dir / friendly_platform_name
                    dest_dir.mkdir(parents=True, exist_ok=True)
                    dest_file_path = dest_dir / binary_file_path.name

                    print(f"::info::Copying '{binary_file_path}' to '{dest_file_path}' for platform '{friendly_platform_name}'")
                    shutil.copy2(binary_file_path, dest_file_path)

                except IndexError:
                    print(f"::warning::Could not extract platform target name from path: {binary_file_path}. Skipping.")
                    continue
                except Exception as e:
                    print(f"::error::Error copying file {binary_file_path} to {dest_file_path}: {e}")
                    continue

    # 5. 모든 필수 플랫폼의 바이너리가 준비되었는지 확인 (모듈 레벨 변수 사용)
    missing_platforms = required_platforms - found_platforms
    if missing_platforms:
        print(f"::error::Missing required platform binaries for: {', '.join(missing_platforms)}")
        return False # 필수 바이너리가 누락되었으므로 실패

    if not found_platforms:
         # required_platforms가 비어있지 않다면 이 조건은 사실상 위의 missing_platforms 체크에 포함됨.
         # 하지만 required_platforms가 비어있는 경우 (모든 플랫폼이 필수가 아닐 때)를 위해 남겨둠.
         # 현재는 모든 플랫폼이 필수라고 가정하므로 이 블록은 실행되지 않을 가능성이 높음.
        print("::error::No binary files were found at all.")
        return False


    print("::info::Finished preparing release assets. All required platforms found.")
    return True


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Prepare release assets from downloaded build artifacts.")
    parser.add_argument("--input-dir", required=True, help="Root directory containing downloaded artifacts.")
    parser.add_argument("--output-dir", required=True, help="Directory to place prepared release assets.")
    parser.add_argument("--prop-file", required=True, help="Path to the gradle.properties file.")
    args = parser.parse_args()

    # prepare_assets 함수 실행 및 결과에 따라 종료 코드 설정
    if not prepare_assets(args.input_dir, args.output_dir, args.prop_file):
        print("::error::Release asset preparation failed.")
        sys.exit(1) # 실패 시 1로 종료

    print("Release asset preparation completed successfully.")
