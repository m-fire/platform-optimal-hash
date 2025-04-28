# .github/scripts/validate_version_consistency.py
# 입력 버전과 gradle.properties의 libVersion 일치 여부 검증
import argparse
import os
import sys
from pathlib import Path


def get_gradle_property(prop_file, key):
    """gradle.properties 파일에서 속성 값 읽기"""
    prop_path = Path(prop_file)
    if not prop_path.is_file():
        print(f"::error::Gradle properties file not found: {prop_file}")
        return None

    try:
        with open(prop_path, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith('#'):
                    continue
                if line.startswith(key + '=') or line.startswith(key + ' ='):
                    return line.split('=', 1)[1].strip()
    except Exception as e:
        print(f"::error::Error reading {prop_file}: {e}")
        return None
    return None  # 해당 키가 파일에 없는 경우


def set_github_output(name, value):
    """GitHub Actions 워크플로우를 위한 출력 설정"""
    github_output_file = os.getenv('GITHUB_OUTPUT')
    if github_output_file:
        print(f"Setting output: {name}={value}")
        with open(github_output_file, 'a', encoding='utf-8') as f:
            # 출력값에 개행 문자가 포함될 수 있으므로 멀티라인 처리 고려
            # 여기서는 버전 문자열이므로 단순 쓰기
            f.write(f"{name}={value}\n")
    else:
        print(f"::warning::Unable to set output '{name}'. GITHUB_OUTPUT environment variable not set.")


def validate_version(expected_version, prop_file="gradle.properties"):
    """버전 일치 검증 및 결과 출력"""
    print(f"Expected version: {expected_version}")
    prop_version = get_gradle_property(prop_file, 'libVersion')

    if prop_version is None:
        print(f"::error::'libVersion' not found or could not be read from {prop_file}.")
        return False  # 오류로 처리

    print(f"Version from {prop_file}: {prop_version}")

    if expected_version != prop_version:
        print(
            f"::error::Input version ('{expected_version}') does not match libVersion in {prop_file} ('{prop_version}').")
        return False  # 버전 불일치

    print("Version check passed.")
    # 성공 시 버전 정보 출력 설정
    set_github_output("version_num", prop_version)
    set_github_output("version_tag", f"v{prop_version}")
    return True


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Validate version consistency between input and gradle.properties.")
    parser.add_argument("--expected-version", required=True,
                        help="The version string expected (e.g., from workflow input).")
    parser.add_argument("--prop-file", default="gradle.properties", help="Path to the gradle.properties file.")
    args = parser.parse_args()

    if not validate_version(args.expected_version, args.prop_file):
        sys.exit(1)  # 실패 시 non-zero exit code 반환
