# .github/scripts/test_generate_release_info.py
import os
import shutil
import sys
import unittest  # unittest 임포트 확인
import zipfile
from pathlib import Path
from tempfile import TemporaryDirectory

# 테스트 대상 스크립트 경로 추가
script_dir = Path(__file__).parent
sys.path.append(str(script_dir))

try:
    # 테스트 대상 스크립트 임포트
    import generate_release_info
except ImportError as e:
    print(f"테스트 대상 모듈 임포트 실패: {e}")
    print(f"스크립트 경로 확인: {script_dir}")
    raise

class TestGenerateReleaseInfo(unittest.TestCase):

    def setUp(self):
        """각 테스트 메서드 실행 전에 호출되는 설정 메서드"""
        self.test_dir = TemporaryDirectory()
        self.mock_assets_dir = Path(self.test_dir.name) / "release-assets"
        self.mock_output_body_file = Path(self.test_dir.name) / "release-body.md"
        self.mock_output_zip_file = Path(self.test_dir.name) / "test-archive.zip"
        self.mock_github_output_path = Path(self.test_dir.name) / "github_output.txt"
        # GITHUB_OUTPUT 파일 생성 및 환경 변수 설정
        self.mock_github_output_path.touch()
        os.environ['GITHUB_OUTPUT'] = str(self.mock_github_output_path)

    def tearDown(self):
        """각 테스트 메서드 실행 후에 호출되는 정리 메서드"""
        self.test_dir.cleanup()
        # 환경 변수 정리
        if 'GITHUB_OUTPUT' in os.environ:
            del os.environ['GITHUB_OUTPUT']

    def _read_github_output(self):
        """Mock GITHUB_OUTPUT 파일 내용 읽기"""
        if self.mock_github_output_path.exists():
            with open(self.mock_github_output_path, 'r', encoding='utf-8') as f:
                return f.read()
        return ""

    def test_normal_case(self):
        """정상적인 경우: 릴리스 정보 생성 성공 및 GITHUB_OUTPUT 확인"""
        self.mock_assets_dir.mkdir()
        # prepare_release_assets.py가 생성하는 구조와 유사하게 Mock 디렉토리 및 파일 생성
        (self.mock_assets_dir / "linux").mkdir()
        (self.mock_assets_dir / "linux" / "my-library.so").touch()
        (self.mock_assets_dir / "windows").mkdir()
        (self.mock_assets_dir / "windows" / "my-library.dll").touch()
        (self.mock_assets_dir / "macos-x64").mkdir()
        (self.mock_assets_dir / "macos-x64" / "my-library.dylib").touch()
        (self.mock_assets_dir / "ios-arm64").mkdir()
        (self.mock_assets_dir / "ios-arm64" / "my-library.dylib").touch()

        version = "1.2.3"

        # generate_body 함수 테스트
        body_path = generate_release_info.generate_body(version, str(self.mock_assets_dir), str(self.mock_output_body_file))
        self.assertIsNotNone(body_path)
        self.assertTrue(self.mock_output_body_file.exists())
        with open(self.mock_output_body_file, 'r', encoding='utf-8') as f:
            content = f.read()
            self.assertIn(f"## Platform Binary Release v{version}", content)
            self.assertIn("- `linux`", content)
            self.assertIn("- `windows`", content)
            self.assertIn("- `macos-x64`", content)
            self.assertIn("- `ios-arm64`", content)


        # create_zip 함수 테스트
        zip_path = generate_release_info.create_zip(version, str(self.mock_assets_dir), str(self.mock_output_zip_file))
        self.assertIsNotNone(zip_path)
        self.assertTrue(self.mock_output_zip_file.exists())
        with zipfile.ZipFile(self.mock_output_zip_file, 'r') as zipf:
            namelist = zipf.namelist()
            # Zip 파일 내 예상 경로 (release-assets 디렉토리 기준 상대 경로)
            expected_files = {
                "linux/my-library.so",
                "windows/my-library.dll",
                "macos-x64/my-library.dylib",
                "ios-arm64/my-library.dylib",
            }
            # Windows 경로 구분자(\)를 /로 변환하여 비교
            self.assertSetEqual({n.replace('\\', '/') for n in namelist}, expected_files)

        # GITHUB_OUTPUT 내용 검증
        generate_release_info.set_github_output("body_path", body_path)
        generate_release_info.set_github_output("zip_path", zip_path)
        outputs = self._read_github_output()
        expected_body_path_str = str(Path(body_path).resolve())
        expected_zip_path_str = str(Path(zip_path).resolve())
        # 경로 비교 시 Windows 경로 구분자 문제 방지
        self.assertIn(f"body_path={expected_body_path_str.replace('\\', '/')}", outputs.replace('\\\\', '\\').replace('\\', '/'))
        self.assertIn(f"zip_path={expected_zip_path_str.replace('\\', '/')}", outputs.replace('\\\\', '\\').replace('\\', '/'))


    def test_empty_assets_directory(self):
        """엣지 케이스: 에셋 디렉토리가 비어 있음"""
        self.mock_assets_dir.mkdir() # 빈 디렉토리 생성
        version = "1.0.0"

        # generate_body 함수 테스트
        body_path = generate_release_info.generate_body(version, str(self.mock_assets_dir), str(self.mock_output_body_file))
        self.assertIsNotNone(body_path)
        self.assertTrue(self.mock_output_body_file.exists())
        with open(self.mock_output_body_file, 'r', encoding='utf-8') as f:
            self.assertIn("(No platform assets found)", f.read())

        # create_zip 함수 테스트
        zip_path = generate_release_info.create_zip(version, str(self.mock_assets_dir), str(self.mock_output_zip_file))
        self.assertIsNotNone(zip_path)
        self.assertTrue(self.mock_output_zip_file.exists())
        with zipfile.ZipFile(self.mock_output_zip_file, 'r') as zipf:
            self.assertEqual(len(zipf.namelist()), 0) # 빈 Zip 파일인지 확인

        # GITHUB_OUTPUT 내용 검증
        generate_release_info.set_github_output("body_path", body_path)
        generate_release_info.set_github_output("zip_path", zip_path)
        outputs = self._read_github_output()
        expected_body_path_str = str(Path(body_path).resolve())
        expected_zip_path_str = str(Path(zip_path).resolve())
        self.assertIn(f"body_path={expected_body_path_str.replace('\\', '/')}", outputs.replace('\\\\', '\\').replace('\\', '/'))
        self.assertIn(f"zip_path={expected_zip_path_str.replace('\\', '/')}", outputs.replace('\\\\', '\\').replace('\\', '/'))


    def test_missing_assets_directory(self):
        """엣지 케이스: 에셋 디렉토리 자체가 없음"""
        # mock_assets_dir를 생성하지 않음
        version = "0.9.0"

        # generate_body 함수 테스트
        body_path = generate_release_info.generate_body(version, str(self.mock_assets_dir), str(self.mock_output_body_file))
        self.assertIsNotNone(body_path)
        self.assertTrue(self.mock_output_body_file.exists())
        with open(body_path, 'r', encoding='utf-8') as f:
            self.assertIn("(No platform assets found)", f.read())

        # create_zip 함수 테스트
        zip_path = generate_release_info.create_zip(version, str(self.mock_assets_dir), str(self.mock_output_zip_file))
        # assets_dir이 없으면 create_zip은 빈 zip 파일을 생성하고 경로를 반환함
        self.assertIsNotNone(zip_path)
        self.assertTrue(self.mock_output_zip_file.exists())
        with zipfile.ZipFile(zip_path, 'r') as zipf:
            self.assertEqual(len(zipf.namelist()), 0) # 빈 Zip 파일인지 확인

        # GITHUB_OUTPUT 내용 검증
        generate_release_info.set_github_output("body_path", body_path)
        generate_release_info.set_github_output("zip_path", zip_path)
        outputs = self._read_github_output()
        expected_body_path_str = str(Path(body_path).resolve())
        expected_zip_path_str = str(Path(zip_path).resolve())
        self.assertIn(f"body_path={expected_body_path_str.replace('\\', '/')}", outputs.replace('\\\\', '\\').replace('\\', '/'))
        self.assertIn(f"zip_path={expected_zip_path_str.replace('\\', '/')}", outputs.replace('\\\\', '\\').replace('\\', '/'))


    def test_no_github_output_env(self):
        """엣지 케이스: GITHUB_OUTPUT 환경 변수 없음"""
        self.mock_assets_dir.mkdir()
        (self.mock_assets_dir / "linux").mkdir()
        (self.mock_assets_dir / "linux" / "my-library.so").touch()

        # 환경 변수 제거
        if 'GITHUB_OUTPUT' in os.environ:
            del os.environ['GITHUB_OUTPUT']
        version = "1.1.0"

        # generate_body 함수 테스트
        body_path = generate_release_info.generate_body(version, str(self.mock_assets_dir), str(self.mock_output_body_file))
        self.assertIsNotNone(body_path)
        self.assertTrue(self.mock_output_body_file.exists())

        # create_zip 함수 테스트
        zip_path = generate_release_info.create_zip(version, str(self.mock_assets_dir), str(self.mock_output_zip_file))
        self.assertIsNotNone(zip_path)
        self.assertTrue(self.mock_output_zip_file.exists())

        # GITHUB_OUTPUT 환경 변수가 없으므로 set_github_output 호출해도 파일에 쓰여지지 않아야 함
        generate_release_info.set_github_output("body_path", body_path) # 이 호출은 경고만 출력해야 함
        generate_release_info.set_github_output("zip_path", zip_path)   # 이 호출은 경고만 출력해야 함

        outputs = self._read_github_output()
        self.assertEqual(outputs, "") # 출력 파일 내용이 비어있는지 확인


if __name__ == '__main__':
    # 테스트 실행 시 모듈 경로 설정 문제 방지
    # sys.argv[0]은 스크립트 이름이므로 무시하고 나머지 인자만 전달
    unittest.main(argv=['first-arg-is-ignored'], exit=False)
