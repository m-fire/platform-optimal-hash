# .github/scripts/test_validate_version_consistency.py
import os
import sys
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

# 테스트 대상 스크립트 경로 추가
script_dir = Path(__file__).parent.parent / '.github' / 'scripts'
sys.path.append(str(script_dir))

try:
    # 테스트 대상 스크립트 임포트
    import validate_version_consistency
except ImportError as e:
    print(f"테스트 대상 모듈 임포트 실패: {e}")
    raise

class TestValidateVersionConsistency(unittest.TestCase):

    def setUp(self):
        """각 테스트 메서드 실행 전에 호출되는 설정 메서드"""
        self.test_dir = TemporaryDirectory()
        self.mock_prop_file = Path(self.test_dir.name) / "gradle.properties"
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

    def _write_props(self, content):
        """테스트용 gradle.properties 파일 내용 작성 헬퍼 함수"""
        with open(self.mock_prop_file, "w", encoding="utf-8") as f:
            f.write(content)

    def _read_github_output(self):
        """Mock GITHUB_OUTPUT 파일 내용 읽기"""
        if self.mock_github_output_path.exists():
            with open(self.mock_github_output_path, 'r', encoding='utf-8') as f:
                return f.read()
        return ""

    def test_version_match(self):
        """정상 케이스: 버전 일치"""
        self._write_props("libVersion=1.0.0\nother=value")
        # 스크립트 실행
        result = validate_version_consistency.validate_version("1.0.0", str(self.mock_prop_file))
        self.assertTrue(result) # 성공 반환 확인
        # GITHUB_OUTPUT 내용 확인
        outputs = self._read_github_output()
        self.assertIn("version_num=1.0.0", outputs)
        self.assertIn("version_tag=v1.0.0", outputs)

    def test_version_mismatch(self):
        """엣지 케이스: 버전 불일치"""
        self._write_props("libVersion=1.0.0")
        # 스크립트 실행
        result = validate_version_consistency.validate_version("1.0.1", str(self.mock_prop_file))
        self.assertFalse(result) # 실패 반환 확인
        # GITHUB_OUTPUT 내용 확인 (출력 없어야 함)
        outputs = self._read_github_output()
        self.assertEqual(outputs, "")

    def test_missing_properties_file(self):
        """엣지 케이스: gradle.properties 파일 없음"""
        # 파일 생성 안 함
        result = validate_version_consistency.validate_version("1.0.0", str(self.mock_prop_file))
        self.assertFalse(result)

    def test_missing_libversion_key(self):
        """엣지 케이스: libVersion 키 없음"""
        self._write_props("otherVersion=1.0.0")
        result = validate_version_consistency.validate_version("1.0.0", str(self.mock_prop_file))
        self.assertFalse(result)

    def test_properties_with_spaces(self):
        """정상 케이스: 속성 정의 시 공백 포함"""
        self._write_props(" libVersion = 1.0.0 ")
        result = validate_version_consistency.validate_version("1.0.0", str(self.mock_prop_file))
        self.assertTrue(result)
        outputs = self._read_github_output()
        self.assertIn("version_num=1.0.0", outputs)
        self.assertIn("version_tag=v1.0.0", outputs)

    def test_properties_with_comments(self):
        """정상 케이스: 주석 포함"""
        self._write_props("# This is a comment\nlibVersion=1.0.0\n# another comment")
        result = validate_version_consistency.validate_version("1.0.0", str(self.mock_prop_file))
        self.assertTrue(result)

    def test_no_github_output_env(self):
        """엣지 케이스: GITHUB_OUTPUT 환경 변수 없음"""
        # 환경 변수 제거 (존재 확인 후)
        if 'GITHUB_OUTPUT' in os.environ:
            del os.environ['GITHUB_OUTPUT']
        self._write_props("libVersion=1.0.0")
        # 스크립트 실행 (성공해야 함)
        result = validate_version_consistency.validate_version("1.0.0", str(self.mock_prop_file))
        self.assertTrue(result)
        # GITHUB_OUTPUT 파일 내용은 비어있어야 함
        outputs = self._read_github_output()
        self.assertEqual(outputs, "")


if __name__ == '__main__':
    # 테스트 실행
    unittest.main(argv=['first-arg-is-ignored'], exit=False)
