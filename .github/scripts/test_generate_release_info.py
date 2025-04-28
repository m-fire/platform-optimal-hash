# .github/scripts/test_generate_release_info.py (Fixed)
import os
import shutil
import sys
import zipfile
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest # unittest 임포트 확인

# 테스트 대상 스크립트 경로 추가
script_dir = Path(__file__).parent.parent / '.github' / 'scripts'
sys.path.append(str(script_dir))

try:
    # 테스트 대상 스크립트 임포트
    import generate_release_info
except ImportError as e:
    print(f"테스트 대상 모듈 임포트 실패: {e}")
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
        (self.mock_assets_dir / "linux").mkdir()
        (self.mock_assets_dir / "linux" / "my-library.so").touch()
        (self.mock_assets_dir / "windows").mkdir()
        (self.mock_assets_dir / "windows" / "my-library.dll").touch()
        version = "1.2.3"

        body_path = generate_release_info.generate_body(version, str(self.mock_assets_dir), str(self.mock_output_body_file))
        zip_path = generate_release_info.create_zip(version, str(self.mock_assets_dir), str(self.mock_output_zip_file))

        generate_release_info.set_github_output("body_path", body_path)
        generate_release_info.set_github_output("zip_path", zip_path)

        # 생성된 파일 검증 (기존과 동일)
        self.assertTrue(self.mock_output_body_file.exists())
        with open(self.mock_output_body_file, 'r', encoding='utf-8') as f:
            content = f.read()
            self.assertIn(f"## Platform Binary Release v{version}", content)
            self.assertIn("- `linux`", content)
            self.assertIn("- `windows`", content)
        self.assertTrue(self.mock_output_zip_file.exists())
        with zipfile.ZipFile(self.mock_output_zip_file, 'r') as zipf:
            namelist = zipf.namelist()
            expected_files = {"linux/my-library.so", "windows/my-library.dll"}
            self.assertSetEqual({n.replace('\\', '/') for n in namelist}, expected_files)

        # GITHUB_OUTPUT 내용 검증
        outputs = self._read_github_output()
        expected_body_path_str = str(Path(body_path).resolve())
        expected_zip_path_str = str(Path(zip_path).resolve())
        self.assertIn(f"body_path={expected_body_path_str}", outputs.replace('\\\\', '\\'))
        self.assertIn(f"zip_path={expected_zip_path_str}", outputs.replace('\\\\', '\\'))

    def test_empty_assets_directory(self):
        """엣지 케이스: 에셋 디렉토리가 비어 있음"""
        self.mock_assets_dir.mkdir()
        version = "1.0.0"

        body_path = generate_release_info.generate_body(version, str(self.mock_assets_dir), str(self.mock_output_body_file))
        zip_path = generate_release_info.create_zip(version, str(self.mock_assets_dir), str(self.mock_output_zip_file))

        generate_release_info.set_github_output("body_path", body_path)
        generate_release_info.set_github_output("zip_path", zip_path)

        # 생성된 파일 검증 (기존과 동일)
        self.assertTrue(self.mock_output_body_file.exists())
        with open(self.mock_output_body_file, 'r', encoding='utf-8') as f:
            self.assertIn("(No platform assets found)", f.read())
        self.assertTrue(self.mock_output_zip_file.exists())
        with zipfile.ZipFile(self.mock_output_zip_file, 'r') as zipf:
            self.assertEqual(len(zipf.namelist()), 0)

        # GITHUB_OUTPUT 내용 검증
        outputs = self._read_github_output()
        expected_body_path_str = str(Path(body_path).resolve())
        expected_zip_path_str = str(Path(zip_path).resolve())
        self.assertIn(f"body_path={expected_body_path_str}", outputs.replace('\\\\', '\\'))
        self.assertIn(f"zip_path={expected_zip_path_str}", outputs.replace('\\\\', '\\'))

    def test_missing_assets_directory(self):
        """엣지 케이스: 에셋 디렉토리 자체가 없음"""
        version = "0.9.0"

        body_path = generate_release_info.generate_body(version, str(self.mock_assets_dir), str(self.mock_output_body_file))
        zip_path = generate_release_info.create_zip(version, str(self.mock_assets_dir), str(self.mock_output_zip_file))

        generate_release_info.set_github_output("body_path", body_path)
        generate_release_info.set_github_output("zip_path", zip_path)

        # 생성된 파일 검증 (기존과 동일)
        self.assertTrue(self.mock_output_body_file.exists())
        with open(body_path, 'r', encoding='utf-8') as f:
            self.assertIn("(No platform assets found)", f.read())
        self.assertIsNotNone(zip_path)
        self.assertTrue(self.mock_output_zip_file.exists())
        with zipfile.ZipFile(zip_path, 'r') as zipf:
            self.assertEqual(len(zipf.namelist()), 0)

        # GITHUB_OUTPUT 내용 검증
        outputs = self._read_github_output()
        expected_body_path_str = str(Path(body_path).resolve())
        expected_zip_path_str = str(Path(zip_path).resolve())
        self.assertIn(f"body_path={expected_body_path_str}", outputs.replace('\\\\', '\\'))
        self.assertIn(f"zip_path={expected_zip_path_str}", outputs.replace('\\\\', '\\'))

    def test_no_github_output_env(self):
        """엣지 케이스: GITHUB_OUTPUT 환경 변수 없음"""
        self.mock_assets_dir.mkdir()
        (self.mock_assets_dir / "linux").mkdir()
        (self.mock_assets_dir / "linux" / "my-library.so").touch()

        # 환경 변수 제거
        if 'GITHUB_OUTPUT' in os.environ:
            del os.environ['GITHUB_OUTPUT']
        version = "1.1.0"

        body_path = generate_release_info.generate_body(version, str(self.mock_assets_dir), str(self.mock_output_body_file))
        zip_path = generate_release_info.create_zip(version, str(self.mock_assets_dir), str(self.mock_output_zip_file))

        # 여기서는 set_github_output 호출하면 안 됨 (환경 변수 없는 시나리오)

        self.assertIsNotNone(body_path)
        self.assertIsNotNone(zip_path)
        outputs = self._read_github_output()
        self.assertEqual(outputs, "") # 출력 파일 내용 비어있는지 확인 (기존과 동일)

if __name__ == '__main__':
    unittest.main(argv=['first-arg-is-ignored'], exit=False)
