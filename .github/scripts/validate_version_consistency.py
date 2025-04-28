# .github/scripts/validate_version_consistency.py
# 입력 버전과 gradle.properties의 libVersion, 최신 Git 태그를 비교 검증하고,
# 필요한 경우 gradle.properties 파일을 업데이트함.
import argparse
import os
import re
import subprocess
import sys
from pathlib import Path

# packaging 라이브러리가 없으면 설치 시도 (워크플로우에서는 미리 설치 권장)
try:
    from packaging import version as packaging_version
except ImportError:
    print("::warning::'packaging' library not found. Attempting to install...")
    try:
        subprocess.check_call([sys.executable, "-m", "pip", "install", "packaging"])
        from packaging import version as packaging_version
        print("::info::'packaging' library installed successfully.")
    except Exception as e:
        print(f"::error::Failed to install 'packaging' library: {e}")
        print("::error::Please install it manually or ensure it's installed in the workflow.")
        sys.exit(1)

def run_git_command(command):
    """Git 명령어를 실행하고 결과를 반환함."""
    try:
        process = subprocess.run(command, capture_output=True, text=True, check=False, encoding='utf-8')
        if process.returncode != 0: # 에러 발생
            # 태그가 없는 경우 등 정상적인 실패는 stderr로 구분 시도
            if "fatal: No names found, cannot describe anything." in process.stderr:
                return None # 태그 없음
            print(f"::error::Git command failed: {' '.join(command)}")
            print(f"::error::Stderr: {process.stderr.strip()}")
            return None
        return process.stdout.strip()
    except FileNotFoundError:
        print("::error::Git command not found. Ensure Git is installed and in PATH.")
        return None
    except Exception as e:
        print(f"::error::Error running Git command {' '.join(command)}: {e}")
        return None

def get_latest_tag():
    """저장소에서 가장 최신 태그를 가져옴 (Semantic Versioning 순)."""
    print("Fetching tags from remote...")
    run_git_command(['git', 'fetch', '--tags', '--force']) # 최신 태그 정보 동기화

    tags_output = run_git_command(['git', 'tag'])
    if not tags_output:
        print("::info::No tags found in the repository.")
        return None

    tags = tags_output.splitlines()
    valid_tags = []
    for t in tags:
        # 'v' 접두사 제거 후 버전 파싱 시도
        tag_name = t[1:] if t.startswith('v') else t
        try:
            # packaging 라이브러리를 사용하여 버전 객체 생성
            ver = packaging_version.parse(tag_name)
            # Pre-release가 아닌 정식 버전 태그만 고려하거나, 필요시 로직 수정
            # if not ver.is_prerelease:
            valid_tags.append(ver)
        except packaging_version.InvalidVersion:
            print(f"::warning::Ignoring invalid tag format: {t}")
            continue

    if not valid_tags:
        print("::info::No valid semantic version tags found.")
        return None

    # 버전 객체를 직접 비교하여 최신 버전 찾기
    latest_version = max(valid_tags)
    print(f"::info::Latest valid tag found: v{latest_version}") # 'v' 붙여서 출력
    return latest_version


def get_gradle_property(prop_file_path, key):
    """gradle.properties 파일에서 지정된 키의 값을 읽음."""
    if not prop_file_path.is_file():
        print(f"::error::Gradle properties file not found: {prop_file_path}")
        return None # Early return

    try:
        with open(prop_file_path, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                # 주석 또는 빈 줄 건너뛰기
                if not line or line.startswith('#') or line.startswith('!'):
                    continue
                # 키=값 형식 확인 (공백 허용)
                match = re.match(rf'^\s*{re.escape(key)}\s*=\s*(.*)', line)
                if match:
                    value = match.group(1).strip()
                    print(f"::info::Found '{key}' in {prop_file_path}: {value}")
                    return value
    except Exception as e:
        print(f"::error::Error reading {prop_file_path}: {e}")
        return None # Early return

    print(f"::warning::Key '{key}' not found in {prop_file_path}.")
    return None


def update_gradle_property(prop_file_path, key, new_value):
    """gradle.properties 파일에서 지정된 키의 값을 업데이트함."""
    if not prop_file_path.is_file():
        print(f"::error::Cannot update - Gradle properties file not found: {prop_file_path}")
        return False # Early return

    try:
        lines = []
        updated = False
        key_found = False
        # 정규식 패턴:
        # 그룹 1: 라인 시작부터 '=' 까지 (키와 '=' 포함, 양쪽 공백 포함)
        # 그룹 2: 값 자체 (공백이나 '#' 제외)
        # 그룹 3: 값 뒤의 공백 및 주석 (선택적)
        pattern = re.compile(rf'^(\s*{re.escape(key)}\s*=\s*)([^\s#]*)(\s*#.*)?$')

        with open(prop_file_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()

        new_lines = []
        for line in lines:
            match = pattern.match(line.rstrip()) # 오른쪽 공백 제거 후 매칭 시도
            if match:
                key_found = True
                current_value = match.group(2)
                comment_part = match.group(3) or '' # 주석 없으면 빈 문자열
                # 현재 값과 새 값이 다를 경우에만 업데이트
                if current_value != new_value:
                    # 그룹 1 (키=부분) + 새 값 + 그룹 3 (주석 부분) + 개행
                    new_line = f"{match.group(1)}{new_value}{comment_part}\n"
                    print(f"::info::Updating '{key}' from '{line.rstrip()}' to '{new_line.rstrip()}'")
                    new_lines.append(new_line)
                    updated = True
                else:
                    new_lines.append(line) # 변경 없으면 원본 라인 유지
            else:
                # 매칭되지 않는 라인은 그대로 유지
                new_lines.append(line)

        # 키를 찾았고 실제 업데이트가 발생한 경우 파일 쓰기
        if key_found and updated:
            with open(prop_file_path, 'w', encoding='utf-8') as f:
                f.writelines(new_lines)
            print(f"::info::Successfully updated '{key}' in {prop_file_path}")
            return True
        elif key_found:
            print(f"::info::Key '{key}' found, but value '{new_value}' is already set. No update needed.")
            return False # 업데이트 필요 없음 (성공으로 간주)
        else:
            print(f"::error::Key '{key}' not found in {prop_file_path}. Cannot update.")
            return False

    except Exception as e:
        print(f"::error::Error updating {prop_file_path}: {e}")
        return False


def set_github_output(name, value):
    """GitHub Actions 워크플로우를 위한 출력 설정 (파일 즉시 닫기)."""
    github_output_file = os.getenv('GITHUB_OUTPUT')
    if not github_output_file:
        print(f"::warning::Unable to set output '{name}'. GITHUB_OUTPUT environment variable not set.")
        return # Early return
    if value is None: # 값 자체가 None일 수 있음 (예: false)
         print(f"::warning::Cannot set output '{name}' because value is None.")
         return # Early return

    print(f"::info::Setting output: {name}={str(value).lower()}") # boolean은 소문자로
    try:
        with open(github_output_file, 'a', encoding='utf-8') as f:
            # 출력값에 개행 문자가 포함될 수 있으므로 멀티라인 처리 고려 (여기서는 단순 문자열)
            f.write(f"{name}={str(value).lower()}\n")
    except Exception as e:
        print(f"::error::Failed to write to GITHUB_OUTPUT file '{github_output_file}': {e}")


def main():
    """메인 실행 함수."""
    parser = argparse.ArgumentParser(description="Validate version consistency and update gradle.properties if needed.")
    parser.add_argument("--expected-version", required=True,
                        help="The version string expected (e.g., 1.0.0, 1.1.0rc1). Should be >= libVersion and latest tag.")
    parser.add_argument("--prop-file", default="gradle.properties", help="Path to the gradle.properties file.")
    args = parser.parse_args()

    prop_file_path = Path(args.prop_file)
    expected_version_str = args.expected_version.lstrip('v') # 입력에서 'v' 제거

    # 1. 입력 버전 파싱
    try:
        expected_version = packaging_version.parse(expected_version_str)
        print(f"::info::Parsed expected version: {expected_version}")
    except packaging_version.InvalidVersion:
        print(f"::error::Invalid expected version format: {args.expected_version}")
        sys.exit(1) # Early return

    # 2. gradle.properties 에서 libVersion 읽기 및 파싱
    lib_version_str = get_gradle_property(prop_file_path, 'libVersion')
    if lib_version_str is None:
        # get_gradle_property 내부에서 에러 메시지 출력됨
        sys.exit(1) # Early return

    try:
        lib_version = packaging_version.parse(lib_version_str)
        print(f"::info::Parsed libVersion from {prop_file_path}: {lib_version}")
    except packaging_version.InvalidVersion:
        # libVersion 파싱 실패 시 경고만 하고 진행할지, 아니면 실패 처리할지 결정 필요
        # 여기서는 실패 처리 (표준 버전 형식을 강제하는 것이 좋음)
        print(f"::error::Invalid libVersion format in {prop_file_path}: {lib_version_str}. Please use PEP 440 format (e.g., 1.0.0, 1.1.0rc1).")
        sys.exit(1) # Early return

    # 3. 최신 태그 읽기 및 파싱
    latest_tag_version = get_latest_tag() # 내부에 파싱 로직 포함, 실패 시 None 반환

    # 4. 버전 비교 검증
    # 검증 1: 입력 버전 >= libVersion
    if expected_version < lib_version:
        print(f"::error::Input version ({expected_version}) must be greater than or equal to libVersion ({lib_version}) in {prop_file_path}.")
        sys.exit(1) # Early return

    # 검증 2: 입력 버전 >= 최신 태그 (태그가 존재할 경우)
    if latest_tag_version and expected_version < latest_tag_version:
        print(f"::error::Input version ({expected_version}) must be greater than or equal to the latest tag version (v{latest_tag_version}).")
        sys.exit(1) # Early return

    print("::info::Version checks passed.")

    # 5. 업데이트 필요 여부 확인 및 실행
    needs_update = expected_version > lib_version
    update_successful = False # 업데이트 시도 결과 추적
    updated_output_value = False # 최종 GITHUB_OUTPUT 값

    if needs_update:
        print(f"::info::Input version ({expected_version}) is newer than libVersion ({lib_version}). Attempting to update {prop_file_path}.")
        # 업데이트 시도, 성공 여부 반환 받음
        update_successful = update_gradle_property(prop_file_path, 'libVersion', expected_version_str)
        if update_successful:
            # 업데이트가 성공적으로 이루어진 경우 (실제 변경 발생)
            print(f"::info::libVersion updated successfully to {expected_version_str}.")
            updated_output_value = True # 커밋 필요
        else:
            # 업데이트 함수가 False 반환 (변경 없거나 오류 발생)
            # update_gradle_property 내부에서 에러 메시지 출력됨
            print(f"::warning::Failed to update libVersion in {prop_file_path} or value was already set.")
            # 실패해도 일단 워크플로우는 계속 진행, 커밋은 안 함
            updated_output_value = False
    else:
        print(f"::info::Input version ({expected_version}) is not newer than libVersion ({lib_version}). No update needed.")
        # 업데이트 필요 없으면 성공으로 간주, 커밋 불필요
        updated_output_value = False

    # 6. 최종 결과 출력 설정
    # 업데이트가 필요했고 성공적으로 완료되었을 때만 updated=true
    set_github_output("updated", updated_output_value)

if __name__ == "__main__":
    main()
