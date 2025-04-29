# .github/scripts/prepare_release_assets.py
import argparse
import os
import re  # 정규식 사용을 위해 re 모듈 임포트
import shutil
import sys
from pathlib import Path

# 필수적으로 포함되어야 할 플랫폼 타겟 목록 정의 (모듈 레벨)
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

# 플랫폼명 매핑 (모듈 레벨)
# 예: linuxX64 -> linux, macosX64 -> macos-x64
# Note: 이제 출력 디렉토리 이름으로 이 맵의 '값' 대신 추출된 플랫폼 타겟 이름(맵의 '키')을 직접 사용합니다.
platform_name_map = {
    "linuxX64": "linux", # 이 매핑은 로그 출력 등에서만 사용될 수 있습니다.
    "windowsX64": "windows",
    "androidNativeArm64": "android-arm64",
    "androidNativeX64": "android-x64",
    "macosArm64": "macos-arm64",
    "macosX64": "macos-x64",
    "iosArm64": "ios-arm64",
    "iosX64": "ios-x64",
    # 필요한 다른 타겟 추가
}

# 파일 확장자 매핑 (플랫폼 타겟별 예상 확장자)
# TODO: 각 플랫폼 타겟별 실제 바이너리 파일 확장자를 정확히 명시하세요.
platform_extensions = {
    "linuxX64": "so",
    "windowsX64": "dll",
    "androidNativeArm64": "so",
    "androidNativeX64": "so",
    "macosArm64": "dylib",
    "macosX64": "dylib",
    "iosArm64": "dylib",
    "iosX64": "dylib",
    # 필요한 다른 타겟의 확장자 추가
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
               따라서 실제 바이너리는 input_dir/all-binaries/ 하위에 있을 것으로 예상됩니다.
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

    # 4. 다운로드된 아티팩트 디렉토리 탐색 및 바이너리 복사
    # 다운로드된 아티팩트는 input_dir/all-binaries/ 하위에 있을 것으로 예상됩니다.
    downloaded_artifact_root = input_dir / "all-binaries"
    if not downloaded_artifact_root.is_dir():
        print(f"::error::Downloaded artifact directory not found: {downloaded_artifact_root}. Expected 'all-binaries' subdirectory.")
        return False # 예상되는 아티팩트 디렉토리가 없으면 실패

    found_platforms = set() # 바이너리를 찾은 플랫폼 타겟 목록
    copied_files_count = 0 # 복사된 파일 개수 카운트

    print(f"::info::Searching for binaries in '{downloaded_artifact_root}'")

    # === 파일 탐색 로직 ===
    # downloaded_artifact_root 하위 전체에서 binary_filename_base를 포함하는 파일을 찾습니다.
    search_pattern = f"**/{binary_filename_base}.*"

    # TODO: 이 탐색 패턴이 실제 빌드된 모든 바이너리 파일을 포함하는지 확인하세요.
    # 예: 파일 이름에 -debug, -release 등의 접미사가 붙는 경우 패턴 수정 필요.
    # 예: my-library-linuxX64-release.so -> search_pattern = f"**/{binary_filename_base}-*.so"

    for binary_file_path in downloaded_artifact_root.glob(search_pattern):
        if binary_file_path.is_file():
            print(f"::info::Found potential binary file: {binary_file_path}")
            # 로깅 추가: 찾은 파일의 downloaded_artifact_root 기준 상대 경로 및 파트 출력
            relative_to_artifact_root = binary_file_path.relative_to(downloaded_artifact_root)
            print(f"::debug::Relative path to artifact root: {relative_to_artifact_root}")
            print(f"::debug::Relative path parts (artifact root): {relative_to_artifact_root.parts}")


            # === 플랫폼 타겟 이름 추출 로직 (개선) ===
            # 파일 경로의 각 부분을 순회하며 known 플랫폼 타겟 이름과 일치하는지 확인합니다.
            # 현재 Mock 및 예상되는 아티팩트 구조: downloaded-artifacts/all-binaries/<platform_target>/releaseShared/<filename>
            # 또는 downloaded-artifacts/all-binaries/library/build/bin/<platform_target>/releaseShared/<filename>
            # 또는 downloaded-artifacts/all-binaries/<platform_target>/<filename> 등 다양할 수 있습니다.
            # TODO: 실제 GitHub Actions 환경에서 다운로드된 아티팩트의 내부 구조를 확인하고,
            # 그 구조에 맞게 플랫폼 타겟 이름을 추출하는 로직을 정확히 구현해야 합니다.
            # 현재는 relative_to_artifact_root의 각 파트에서 known 타겟 이름을 찾습니다.

            platform_target_name = None
            try:
                # 상대 경로의 각 부분을 순회하며 known 플랫폼 타겟 이름과 일치하는지 확인
                for part in relative_to_artifact_root.parts:
                    if part in required_platforms or part in platform_name_map: # required_platforms 또는 매핑 키에 포함된 이름 찾기
                        platform_target_name = part
                        print(f"::info::Extracted platform target '{platform_target_name}' from path part '{part}'.")
                        break # 첫 번째로 찾은 유효한 타겟을 사용

                # 파일 이름 자체에서 패턴 매칭 시도 (경로에 타겟 이름이 없는 경우 대비)
                if platform_target_name is None:
                    match = re.search(rf'{re.escape(binary_filename_base)}_([a-zA-Z0-9]+)\..*', binary_file_path.name)
                    if match:
                        potential_target = match.group(1)
                        if potential_target in required_platforms or potential_target in platform_name_map: # required_platforms 또는 매핑 키에 포함된 이름 찾기
                            platform_target_name = potential_target
                            print(f"::info::Extracted platform target '{platform_target_name}' from filename pattern.")


            except Exception as e:
                print(f"::error::Error processing path {binary_file_path}: {e}. Skipping.")
                continue # 경로 처리 오류 시 건너뛰기


            # 예시 3: 플랫폼 타겟 이름을 추출할 수 없는 경우 (오류 또는 경고)
            if platform_target_name is None:
                print(f"::warning::Could not extract platform target name from file path or name: {binary_file_path}. Skipping.")
                continue # 플랫폼 타겟을 알 수 없으면 해당 파일 건너뛰기


            # 찾은 플랫폼 타겟을 found_platforms 집합에 추가 (유효한 타겟만)
            # platform_target_name이 None이 아닌 경우에만 추가
            if platform_target_name:
                # 이미 위 추출 로직에서 required_platforms 또는 platform_name_map 키에 있는지 확인했으므로
                # 여기서는 바로 found_platforms에 추가합니다.
                found_platforms.add(platform_target_name)
            else:
                # platform_target_name이 None인 경우는 위에서 이미 continue 처리됨.
                pass


            # === 출력 경로 생성 수정 ===
            # 요청에 따라 추출된 플랫폼 타겟 이름 자체를 출력 디렉토리 이름으로 사용합니다.
            # platform_name_map은 더 이상 출력 디렉토리 이름 매핑에 사용되지 않습니다.
            dest_dir = output_dir / platform_target_name # 추출된 platform_target_name 사용
            dest_dir.mkdir(parents=True, exist_ok=True)
            dest_file_path = dest_dir / binary_file_path.name # 원본 파일 이름 사용

            # 로그 출력 시에는 platform_name_map의 친근한 이름 사용 (선택 사항)
            friendly_platform_name_for_log = platform_name_map.get(platform_target_name, platform_target_name)
            if platform_target_name not in platform_name_map:
                print(f"::warning::No specific mapping found for platform target '{platform_target_name}'. Using original name for logging.")


            print(f"::info::Copying '{binary_file_path}' to '{dest_file_path}' for platform '{friendly_platform_name_for_log}'")
            try:
                shutil.copy2(binary_file_path, dest_file_path)
                copied_files_count += 1 # 성공적으로 복사된 파일만 카운트
            except Exception as e:
                print(f"::error::Error copying file {binary_file_path} to {dest_file_path}: {e}")
                # 복사 실패 시 해당 파일 건너뛰기
                continue


    # 5. 모든 필수 플랫폼의 바이너리가 준비되었는지 확인 (모듈 레벨 변수 사용)
    missing_platforms = required_platforms - found_platforms
    if missing_platforms:
        print(f"::error::Missing required platform binaries for: {', '.join(missing_platforms)}")
        # TODO: 필수 바이너리가 누락된 경우, 이미 복사된 파일들을 그대로 둘지 아니면 출력 디렉토리를 비울지 결정해야 합니다.
        # 현재는 복사된 파일들을 그대로 둡니다.
        return False # 필수 바이너리가 누락되었으므로 실패

    if copied_files_count == 0 and required_platforms:
        # 필수 플랫폼은 지정되었는데 복사된 파일이 하나도 없다면 문제 상황
        print("::error::No binary files were successfully copied, but required platforms were specified.")
        return False
    elif copied_files_count == 0 and not required_platforms:
        # 필수 플랫폼은 지정되지 않았고 복사된 파일도 없다면 성공으로 간주 가능
        print("::info::No binary files were successfully copied, and no required platforms were specified.")
        pass # 성공으로 간주
    elif copied_files_count > 0 and not required_platforms:
        # 필수 플랫폼은 지정되지 않았지만 일부 파일이 복사되었다면 성공
        print(f"::info::{copied_files_count} binary files were successfully copied.")
        pass # 성공으로 간주


    print("::info::Finished preparing release assets. All required platforms found." if required_platforms else "::info::Finished preparing release assets. No required platforms specified.")
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
