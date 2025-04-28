# .github/scripts/test_prepare_release_assets.py
import os
import shutil
import sys
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

# 테스트 대상 스크립트 경로 추가 (프로젝트 구조에 맞게 조정 필요)
script_dir = Path(__file__).parent.parent / '.github' / 'scripts'
sys.path.append(str(script_dir))

# 테스트 대상 모듈 임포트 시도
try:
    import prepare_release_assets
except ImportError as e:
    print(f"테스트 대상 모듈 임포트 실패: {e}")
    print(f"스크립트 경로 확인: {script_dir}")
    # 테스트 실행 불가 시 에러 발생
    raise

class TestPrepareReleaseAssets(unittest.TestCase):

    def setUp(self):
        """각 테스트 전에 임시 디렉토리 및 파일 설정"""
        self.test_dir = TemporaryDirectory()
        self.mock_input_dir = Path(self.test_dir.name) / "downloaded-artifacts"
        self.mock_output_dir = Path(self.test_dir.name) / "release-assets"
        self.mock_prop_file = Path(self.test_dir.name) / "gradle.properties"

        # Mock gradle.properties 생성
        with open(self.mock_prop_file, "w", encoding="utf-8") as f:
            f.write("otherProp=value\n")
            f.write("binaryFilename=my-library\n")  # 테스트용 바이너리 이름

        # Mock 입력 디렉토리 구조 및 더미 바이너리 파일 생성
        self.mock_input_dir.mkdir(parents=True, exist_ok=True)
        # 예시: non-apple 아티팩트 디렉토리
        non_apple_dir = self.mock_input_dir / "non-apple-binaries" / "library" / "build" / "bin"
        (non_apple_dir / "linuxX64" / "releaseShared").mkdir(parents=True, exist_ok=True)
        (non_apple_dir / "linuxX64" / "releaseShared" / "my-library.so").touch()
        (non_apple_dir / "windowsX64" / "releaseShared").mkdir(parents=True, exist_ok=True)
        (non_apple_dir / "windowsX64" / "releaseShared" / "my-library.dll").touch()

        # 예시: apple 아티팩트 디렉토리
        apple_dir = self.mock_input_dir / "apple-binaries" / "library" / "build" / "bin"
        (apple_dir / "macosX64" / "releaseShared").mkdir(parents=True, exist_ok=True)
        (apple_dir / "macosX64" / "releaseShared" / "my-library.dylib").touch()
        (apple_dir / "iosArm64" / "releaseShared").mkdir(parents=True, exist_ok=True)
        (apple_dir / "iosArm64" / "releaseShared" / "my-library.dylib").touch()

    def tearDown(self):
        """각 테스트 후 임시 디렉토리 정리"""
        self.test_dir.cleanup()

    def test_normal_case(self):
        """정상적인 경우: 에셋 준비 성공 테스트"""
        result = prepare_release_assets.prepare_assets(
            str(self.mock_input_dir), str(self.mock_output_dir), str(self.mock_prop_file)
        )
        self.assertTrue(result)
        # 출력 디렉토리 및 파일 존재 확인
        self.assertTrue((self.mock_output_dir / "linux" / "my-library.so").exists())
        self.assertTrue((self.mock_output_dir / "windows" / "my-library.dll").exists())
        self.assertTrue((self.mock_output_dir / "macos-x64" / "my-library.dylib").exists())
        self.assertTrue((self.mock_output_dir / "ios-arm64" / "my-library.dylib").exists())
        # 다른 플랫폼 파일은 없어야 함 (예시)
        self.assertFalse((self.mock_output_dir / "android-x64").exists())

    def test_missing_properties_file(self):
        """엣지 케이스: gradle.properties 파일 없음"""
        os.remove(self.mock_prop_file)  # 파일 삭제
        result = prepare_release_assets.prepare_assets(
            str(self.mock_input_dir), str(self.mock_output_dir), str(self.mock_prop_file)
        )
        self.assertFalse(result)  # 실패해야 함

    def test_missing_binary_filename_property(self):
        """엣지 케이스: gradle.properties에 binaryFilename 없음"""
        with open(self.mock_prop_file, "w", encoding="utf-8") as f:
            f.write("otherProp=value\n")  # binaryFilename 누락
        result = prepare_release_assets.prepare_assets(
            str(self.mock_input_dir), str(self.mock_output_dir), str(self.mock_prop_file)
        )
        self.assertFalse(result)  # 실패해야 함

    def test_missing_input_directory(self):
        """엣지 케이스: 입력 디렉토리 없음"""
        shutil.rmtree(self.mock_input_dir)  # 디렉토리 삭제
        result = prepare_release_assets.prepare_assets(
            str(self.mock_input_dir), str(self.mock_output_dir), str(self.mock_prop_file)
        )
        self.assertFalse(result)  # 실패해야 함

    def test_missing_specific_binary(self):
        """엣지 케이스: 특정 플랫폼 바이너리 누락"""
        # linux 바이너리 삭제
        os.remove(
            self.mock_input_dir / "non-apple-binaries" / "library" / "build" / "bin" / "linuxX64" / "releaseShared" / "my-library.so")
        result = prepare_release_assets.prepare_assets(
            str(self.mock_input_dir), str(self.mock_output_dir), str(self.mock_prop_file)
        )
        self.assertTrue(result)  # 스크립트는 경고만 출력하고 성공 처리함
        # 출력 디렉토리 확인 (linux 제외)
        self.assertFalse((self.mock_output_dir / "linux").exists())
        self.assertTrue((self.mock_output_dir / "windows" / "my-library.dll").exists())

    def test_empty_input_directory(self):
        """엣지 케이스: 입력 디렉토리는 있으나 내용물(바이너리) 없음"""
        shutil.rmtree(self.mock_input_dir)  # 기존 내용 삭제
        self.mock_input_dir.mkdir()  # 빈 디렉토리 생성
        result = prepare_release_assets.prepare_assets(
            str(self.mock_input_dir), str(self.mock_output_dir), str(self.mock_prop_file)
        )
        self.assertFalse(result)  # 바이너리가 없으므로 실패 처리
        self.assertFalse(self.mock_output_dir.exists())  # 출력 디렉토리도 생성되지 않아야 함 (혹은 비어있음)


if __name__ == '__main__':
    unittest.main(argv=['first-arg-is-ignored'], exit=False)
