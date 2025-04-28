# .github/scripts/prepare_release_assets.py
# 다운로드된 아티팩트를 release-assets/<platform>/<binaryFilename>.<ext> 구조로 정리.
import argparse
import shutil
from pathlib import Path

# 플랫폼명과 Gradle 타겟 디렉토리 매핑 (KMP 표준 bin 디렉토리 구조 기반)
PLATFORM_MAPPING = {
    "linuxX64": "linux",
    "windowsX64": "windows",
    "androidNativeArm64": "android-arm64",
    "androidNativeX64": "android-x64",
    "macosArm64": "macos-arm64",
    "macosX64": "macos-x64",
    "iosArm64": "ios-arm64",
    "iosX64": "ios-x64",
    # XCFrameworks 는 별도 처리 필요할 수 있음
}

# 라이브러리 확장자 매핑
LIB_EXTENSIONS = {
    "linux": ".so",
    "windows": ".dll",
    "android-arm64": ".so",
    "android-x64": ".so",
    "macos-arm64": ".dylib",
    "macos-x64": ".dylib",
    "ios-arm64": ".dylib",  # Static framework 내부의 dylib or framework 자체
    "ios-x64": ".dylib",  # Static framework 내부의 dylib or framework 자체
}


def get_gradle_property(prop_file, key):
    """gradle.properties 파일에서 속성 값 읽기"""
    try:
        with open(prop_file, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if line.startswith(key + '=') or line.startswith(key + ' ='):
                    return line.split('=', 1)[1].strip()
    except FileNotFoundError:
        print(f"::error::Gradle properties file not found: {prop_file}")
        return None
    except Exception as e:
        print(f"::error::Error reading {prop_file}: {e}")
        return None
    return None


def find_binaries(input_dir, binary_filename):
    """
    다운로드된 아티팩트 디렉토리에서 플랫폼별 바이너리 경로 찾기
    input_dir: download-artifact 액션으로 다운로드된 최상위 경로
               (내부에 non-apple-binaries, apple-binaries 등의 디렉토리 포함)
    """
    found_files = {}  # {platform_name: binary_path}

    input_path = Path(input_dir)
    if not input_path.is_dir():
        print(f"::error::Input directory not found: {input_dir}")
        return found_files

    print(f"Searching for binaries in: {input_dir}")

    # KMP 빌드 출력 경로 패턴 검색 (예: .../library/build/bin/<target>/releaseShared/)
    # download-artifact는 각 아티팩트를 하위 디렉토리에 저장함
    for gradle_target, platform_name in PLATFORM_MAPPING.items():
        lib_ext = LIB_EXTENSIONS.get(platform_name, "")
        expected_filename = f"{binary_filename}{lib_ext}"
        # glob 패턴으로 검색 (하위 디렉토리 포함)
        # 예: downloaded-artifacts/non-apple-binaries/library/build/bin/linuxX64/releaseShared/mybinary.so
        # 예: downloaded-artifacts/apple-binaries/library/build/bin/macosX64/releaseShared/mybinary.dylib
        search_pattern = f"**/{gradle_target}/releaseShared/{expected_filename}"

        print(f"Searching for {platform_name} with pattern: {search_pattern}")
        possible_files = list(input_path.glob(search_pattern))

        if not possible_files:
            print(f"::warning::Binary not found for platform: {platform_name} (target: {gradle_target})")
            continue

        # 여러 파일이 찾아진 경우 (가능성은 낮음), 첫 번째 파일 사용
        if len(possible_files) > 1:
            print(f"::warning::Multiple files found for {platform_name}, using first one: {possible_files[0]}")

        found_files[platform_name] = possible_files[0]
        print(f"Found {platform_name}: {possible_files[0]}")

    # TODO: XCFramework 처리 추가 (필요 시)
    # xcframework_path = list(input_path.glob("**/XCFrameworks/release/*.xcframework"))
    # if xcframework_path:
    #    ...

    return found_files


def prepare_assets(input_dir, output_dir, prop_file):
    """릴리즈 에셋 준비"""
    binary_filename = get_gradle_property(prop_file, 'binaryFilename')
    if not binary_filename:
        print("::error::binaryFilename not found in gradle.properties.")
        return False

    print(f"Binary base name: {binary_filename}")

    found_binaries = find_binaries(input_dir, binary_filename)
    if not found_binaries:
        print("::error::No binaries found to prepare.")
        return False

    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    print(f"Preparing assets in: {output_dir}")

    for platform_name, src_path in found_binaries.items():
        lib_ext = LIB_EXTENSIONS.get(platform_name, "")
        dest_filename = f"{binary_filename}{lib_ext}"
        platform_dest_dir = output_path / platform_name
        platform_dest_dir.mkdir(exist_ok=True)
        dest_path = platform_dest_dir / dest_filename

        try:
            print(f"Copying {src_path} to {dest_path}")
            shutil.copy2(src_path, dest_path)  # 메타데이터 포함 복사
        except Exception as e:
            print(f"::error::Failed to copy {src_path} to {dest_path}: {e}")
            return False

    print("Asset preparation completed successfully.")
    return True


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Prepare release assets from downloaded artifacts.")
    parser.add_argument("--input-dir", required=True, help="Directory containing downloaded artifacts.")
    parser.add_argument("--output-dir", required=True, help="Directory to place prepared release assets.")
    parser.add_argument("--prop-file", default="gradle.properties", help="Path to gradle.properties file.")
    args = parser.parse_args()

    if not prepare_assets(args.input_dir, args.output_dir, args.prop_file):
        exit(1)
