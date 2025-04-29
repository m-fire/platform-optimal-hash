# .github/scripts/test_prepare_release_assets.py
import os
import shutil
import sys
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

# 테스트 대상 스크립트 경로 추가
script_dir = Path(__file__).parent
sys.path.append(str(script_dir))

# 테스트 대상 모듈 임포트 시도
try:
    import prepare_release_assets
    # prepare_release_assets 스크립트에서 모듈 레벨로 이동한 변수들을 직접 임포트
    from prepare_release_assets import required_platforms, platform_name_map, platform_extensions
except ImportError as e:
    print(f"테스트 대상 모듈 임포트 실패: {e}")
    print(f"스크립트 경로 확인: {script_dir}")
    # 테스트 실행 불가 시 에러 발생
    raise

class TestPrepareReleaseAssets(unittest.TestCase):

    def setUp(self):
        """각 테스트 전에 임시 디렉토리 및 파일 설정"""
        self.test_dir = TemporaryDirectory()
        # 다운로드된 아티팩트의 임시 루트 디렉토리
        self.mock_input_dir = Path(self.test_dir.name) / "downloaded-artifacts"
        # 준비된 릴리즈 에셋이 저장될 임시 출력 디렉토리
        self.mock_output_dir = Path(self.test_dir.name) / "release-assets"
        # 임시 gradle.properties 파일 경로
        self.mock_prop_file = Path(self.test_dir.name) / "gradle.properties"

        # Mock gradle.properties 생성 (테스트에 필요한 속성 포함)
        with open(self.mock_prop_file, "w", encoding="utf-8") as f:
            f.write("otherProp=value\n")
            # 테스트용 바이너리 이름 설정 (실제 프로젝트의 gradle.properties와 일치해야 함)
            f.write("binaryFilename=my-library\n")

        # Mock 입력 디렉토리 생성
        self.mock_input_dir.mkdir(parents=True, exist_ok=True)

        # prepare_release_assets 스크립트에서 임포트한 required_platforms 목록을 참조하여 테스트에 사용
        self.all_required_platforms = required_platforms
        self.platform_extensions = platform_extensions # 임포트한 확장자 맵 사용


    def tearDown(self):
        """각 테스트 후 임시 디렉토리 정리"""
        self.test_dir.cleanup()

    def _create_mock_artifact_structure(self, platform_target, binary_name, extension):
        """
        임시 입력 디렉토리 내에 단일 아티팩트 및 특정 플랫폼 구조를 생성하고 더미 바이너리 파일을 만듭니다.
        Mock 아티팩트 구조: downloaded-artifacts/all-binaries/library/build/bin/platform_target/releaseShared/binary_name.extension
        platform_target: KMP 플랫폼 타겟 이름 (예: linuxX64, macosX64)
        binary_name: 바이너리 기본 이름 (gradle.properties의 binaryFilename과 일치)
        extension: 바이너리 파일 확장자 (예: so, dll, dylib)
        """
        # 새로운 Mock 아티팩트 구조: input_dir / all-binaries / library/build/bin / platform_target / releaseShared / binary_name.extension
        binary_path = self.mock_input_dir / "all-binaries" / "library" / "build" / "bin" / platform_target / "releaseShared" / f"{binary_name}.{extension}"
        binary_path.parent.mkdir(parents=True, exist_ok=True)
        binary_path.touch()  # 더미 파일 생성
        print(f"Created mock binary: {binary_path}")
        return binary_path  # 생성된 파일 경로 반환

    def test_all_platforms_present(self):
        """정상 케이스: 모든 예상 플랫폼의 바이너리가 존재할 때"""
        binary_base = "my-library"  # gradle.properties에 설정된 이름과 일치

        # 모든 required_platforms에 대해 mock 바이너리 파일 생성
        # prepare_release_assets에서 임포트한 required_platforms 및 platform_extensions 사용
        for platform in required_platforms:
            extension = self.platform_extensions.get(platform)
            if extension:
                self._create_mock_artifact_structure(platform, binary_base, extension)
            else:
                print(f"::warning::Missing extension mapping for platform: {platform}. Cannot create mock binary.")

        # prepare_assets 함수 실행
        result = prepare_release_assets.prepare_assets(
            str(self.mock_input_dir), str(self.mock_output_dir), str(self.mock_prop_file)
        )

        # 결과 검증: 모든 필수 바이너리를 찾았으므로 True를 반환해야 함
        self.assertTrue(result, "prepare_assets should return True when all required binaries are found")

        # 출력 디렉토리 구조 및 파일 존재 확인 (required_platforms에 해당하는 모든 파일 확인)
        # prepare_release_assets.py 스크립트가 추출된 플랫폼 타겟 이름으로 출력 디렉토리를 생성함
        expected_output_files = [
            self.mock_output_dir / p / f"{binary_base}.{self.platform_extensions.get(p, 'bin')}" # 추출된 플랫폼 타겟 이름(p) 사용
            for p in required_platforms # 임포트한 required_platforms 사용
            if self.platform_extensions.get(p) # 확장자 정보가 있는 경우만
        ]

        for expected_file in expected_output_files:
            self.assertTrue(expected_file.exists(), f"Expected output file not found: {expected_file}")
            print(f"Verified output file: {expected_file}")

    def test_missing_specific_platform_binary(self):
        """엣지 케이스: 특정 필수 플랫폼의 바이너리가 누락된 경우 (스크ript 실패 예상)"""
        binary_base = "my-library"

        # required_platforms 중 일부만 Mock 바이너리 생성 (예: linuxX64, windowsX64 만)
        # 이렇게 하면 일부 필수 플랫폼 (macos, ios 등)이 누락됩니다.
        platforms_to_create = {"linuxX64", "windowsX64"}
        platform_extensions_subset = {
            "linuxX64": "so",
            "windowsX64": "dll",
        }

        for platform in platforms_to_create:
            extension = platform_extensions_subset.get(platform)
            if extension:
                self._create_mock_artifact_structure(platform, binary_base, extension)


        # prepare_assets 함수 실행
        result = prepare_release_assets.prepare_assets(
            str(self.mock_input_dir), str(self.mock_output_dir), str(self.mock_prop_file)
        )

        # 결과 검증: 필수 바이너리가 누락되었으므로 False를 반환해야 함
        self.assertFalse(result, "prepare_assets should return False when required binaries are missing")

        # 스크립트가 찾은 파일들은 출력 디렉토리에 복사되었는지 확인
        # 이 경우 linuxX64와 windowsX64 바이너리가 복사되었어야 합니다.
        copied_output_files = [
            self.mock_output_dir / p / f"{binary_base}.{platform_extensions_subset.get(p, 'bin')}" # 추출된 플랫폼 타겟 이름(p) 사용
            for p in platforms_to_create # Mock으로 생성한 플랫폼만 확인
            if platform_extensions_subset.get(p)
        ]
        for copied_file in copied_output_files:
            self.assertTrue(copied_file.exists(), f"Copied output file not found: {copied_file}")

        # 출력 디렉토리가 비어있지 않음을 확인 (찾은 파일이 복사되었으므로)
        self.assertTrue(list(self.mock_output_dir.iterdir()), "Output directory should not be empty if some binaries were copied")


    def test_no_binaries_found(self):
        """엣지 케이스: 예상 패턴과 일치하는 바이너리가 하나도 없는 경우"""
        # 어떤 mock 바이너리 파일도 생성하지 않음 (모든 required_platforms 누락 상황)

        # prepare_assets 함수 실행
        result = prepare_release_assets.prepare_assets(
            str(self.mock_input_dir), str(self.mock_output_dir), str(self.mock_prop_file)
        )

        # 결과 검증: 바이너리를 하나도 찾지 못했으므로 False를 반환해야 함
        self.assertFalse(result, "prepare_assets should return False when no binaries are found")

        # 출력 디렉토리가 존재하고 비어 있는지 확인
        self.assertTrue(self.mock_output_dir.exists(), "Output directory should exist even if no binaries are found")
        self.assertFalse(list(self.mock_output_dir.iterdir()), "Output directory should be empty if no binaries are found")


    def test_missing_artifact_directory(self):
        """엣지 케이스: 다운로드된 아티팩트 디렉토리 자체가 없는 경우 (필수 플랫폼 누락 예상)"""
        # self.mock_input_dir / "all-binaries" 디렉토리를 생성하지 않음

        # prepare_assets 함수 실행
        result = prepare_release_assets.prepare_assets(
            str(self.mock_input_dir), str(self.mock_output_dir), str(self.mock_prop_file)
        )

        # 결과 검증: 다운로드된 아티팩트 디렉토리가 없으므로 False를 반환해야 함
        self.assertFalse(result, "prepare_assets should return False if the downloaded artifact directory is missing")

        # 출력 디렉토리가 존재하지만 비어 있는지 확인 (스크립트 로직에 따름)
        # 스크립트는 실패하더라도 출력 디렉토리를 생성하므로 이와 같이 검증합니다.
        self.assertTrue(self.mock_output_dir.exists(), "Output directory should exist even if downloaded artifact directory is missing")
        self.assertFalse(list(self.mock_output_dir.iterdir()), "Output directory should be empty if downloaded artifact directory is missing")


    def test_incorrect_binary_filename_in_properties(self):
        """엣지 케이스: gradle.properties의 binaryFilename이 실제와 다른 경우"""
        # gradle.properties에 잘못된 바이너리 이름 설정
        with open(self.mock_prop_file, "w", encoding="utf-8") as f:
            f.write("binaryFilename=wrong-name\n")

        binary_base = "my-library"  # 실제 파일 이름은 my-library

        # mock 바이너리 파일 생성 (required_platforms에 포함된 플랫폼으로)
        # Binary Filename이 틀렸으므로 스크립트는 이 파일을 찾지 못할 것입니다.
        platform_to_create = "linuxX64"
        extension = self.platform_extensions.get(platform_to_create)
        if extension:
            self._create_mock_artifact_structure(platform_to_create, binary_base, extension)


        # prepare_assets 함수 실행
        result = prepare_release_assets.prepare_assets(
            str(self.mock_input_dir), str(self.mock_output_dir), str(self.mock_prop_file)
        )

        # 결과 검증: binaryFilename이 틀려서 파일을 찾지 못했으므로 False를 반환해야 함 (모든 required_platforms 누락으로 간주)
        self.assertFalse(result, "prepare_assets should return False if binaryFilename in properties is incorrect")

        # 출력 디렉토리가 생성되고 비어 있는지 확인 (스크립트 로직에 따름)
        self.assertTrue(self.mock_output_dir.exists(), "Output directory should exist even if binaryFilename is incorrect")
        self.assertFalse(list(self.mock_output_dir.iterdir()), "Output directory should be empty if binaryFilename is incorrect")


    def test_missing_gradle_properties_file(self):
        """엣지 케이스: gradle.properties 파일 자체가 없는 경우"""
        # gradle.properties 파일 삭제
        os.remove(self.mock_prop_file)

        # prepare_assets 함수 실행
        result = prepare_release_assets.prepare_assets(
            str(self.mock_input_dir), str(self.mock_output_dir), str(self.mock_prop_file)
        )

        # 결과 검증: properties 파일을 찾지 못했으므로 False를 반환해야 함
        self.assertFalse(result, "prepare_assets should return False if gradle.properties is missing")

        # 출력 디렉토리가 생성되지 않는지 확인
        self.assertFalse(self.mock_output_dir.exists(), "Output directory should not be created if gradle.properties is missing")


if __name__ == '__main__':
    # 테스트 실행 시 모듈 경로 설정 문제 방지
    # sys.argv[0]은 스크립트 이름이므로 무시하고 나머지 인자만 전달
    unittest.main(argv=['first-arg-is-ignored'], exit=False)
