# .github/scripts/generate_release_info.py
# 릴리스 본문과 Zip 아카이브를 생성하고, 파일 경로를 GitHub Actions 출력으로 설정.
import argparse
import os
import sys  # sys 모듈 임포트 추가
import zipfile
from pathlib import Path


def set_github_output(name, value):
    """GitHub Actions 워크플로우를 위한 출력 설정 (파일 즉시 닫기)"""
    github_output_file = os.getenv('GITHUB_OUTPUT')
    if not github_output_file:
        print(f"::warning::Unable to set output '{name}'. GITHUB_OUTPUT environment variable not set.")
        return
    if not value:
        print(f"::warning::Cannot set output '{name}' because value is empty.")
        return

    print(f"Setting output: {name}={value}")
    try:
        # 파일을 append 모드로 열고 즉시 닫음
        with open(github_output_file, 'a', encoding='utf-8') as f:
            f.write(f"{name}={value}\n")
    except Exception as e:
        print(f"::error::Failed to write to GITHUB_OUTPUT file '{github_output_file}': {e}")


def generate_body(version, assets_dir, output_file):
    """릴리스 본문 파일 생성"""
    output_path = Path(output_file)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    assets_path = Path(assets_dir)

    print(f"Generating release body for version {version}")

    # ***** 수정: assets_path 존재 및 디렉토리 여부 확인 *****
    platforms = []
    if assets_path.is_dir():
        platforms = sorted([p.name for p in assets_path.iterdir() if p.is_dir()])
        print(f"Found platforms in {assets_dir}: {platforms}")
    else:
        print(f"::warning::Assets directory not found or is not a directory: {assets_dir}")

    try:
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(f"## Platform Binary Release v{version}\n\n")
            f.write("This release includes pre-compiled binaries for various platforms.\n")
            f.write("Binaries are provided as individual assets and within a single zip archive.\n\n")
            f.write("**Included Platforms:**\n")
            if platforms:
                for platform in platforms:
                    f.write(f"- `{platform}`\n")
            else:
                f.write("- (No platform assets found)\n")
            f.write("\n")
            # 추가적인 릴리스 노트 내용 삽입 가능
    except Exception as e:
        print(f"::error::Failed to write release body to {output_path}: {e}")
        return None

    print(f"Release body written to: {output_path}")
    return str(output_path.resolve())  # 절대 경로 반환


def create_zip(version, assets_dir, output_file):
    """릴리즈 에셋 Zip 아카이브 생성"""
    output_path = Path(output_file)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    assets_path = Path(assets_dir)

    if not assets_path.is_dir():
        print(f"::warning::Assets directory not found: {assets_dir}. Creating an empty zip file.")
        # 에셋 디렉토리가 없어도 빈 zip 파일 생성 시도 (릴리즈 액션 호환성)
        try:
            with zipfile.ZipFile(output_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
                pass  # 빈 zip 파일 생성
            print(f"Empty zip archive created: {output_path}")
            return str(output_path.resolve())
        except Exception as e:
            print(f"::error::Failed to create empty zip archive: {e}")
        return None

    print(f"Creating zip archive for version {version} from {assets_dir}")
    try:
        with zipfile.ZipFile(output_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
            for root, _, files in os.walk(assets_path):
                for file in files:
                    file_path = Path(root) / file
                    # zip 파일 내 경로: <platform>/<filename>
                    archive_name = file_path.relative_to(assets_path)
                    zipf.write(file_path, arcname=archive_name)
                    print(f"Adding to zip: {archive_name}")
        print(f"Zip archive created: {output_path}")
        return str(output_path.resolve())  # 절대 경로 반환
    except Exception as e:
        print(f"::error::Failed to create zip archive: {e}")
        return None


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate release body and zip archive.")
    parser.add_argument("--version", required=True, help="Release version number (e.g., 1.0.0).")
    parser.add_argument("--assets-dir", required=True, help="Directory containing prepared release assets.")
    parser.add_argument("--output-body-file", required=True, help="Path to write the release body markdown file.")
    parser.add_argument("--output-zip-file", required=True, help="Path to write the output zip archive.")
    args = parser.parse_args()

    body_file_path = generate_body(args.version, args.assets_dir, args.output_body_file)
    zip_file_path = create_zip(args.version, args.assets_dir, args.output_zip_file)

    # 생성 성공 여부와 관계없이 출력 설정 시도 (경로가 None일 수 있음)
    set_github_output("body_path", body_file_path)
    set_github_output("zip_path", zip_file_path)

    if not body_file_path:  # 본문 생성 실패 시 주 에러로 간주
        print("::error::Failed to generate release body.")
        sys.exit(1)  # sys.exit 사용

    print("Release info generation completed.")
