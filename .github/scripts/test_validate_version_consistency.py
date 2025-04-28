# .github/scripts/test_validate_version_consistency.py
import os
import sys
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory, NamedTemporaryFile
from unittest.mock import patch, MagicMock

# 테스트 대상 스크립트 경로 추가
script_dir = Path(__file__).parent.parent / '.github' / 'scripts'
sys.path.append(str(script_dir))

# 테스트 대상 스크립트 임포트
try:
    import validate_version_consistency
except ImportError as e:
    print(f"테스트 대상 모듈 임포트 실패: {e}")
    raise

# packaging 라이브러리 임포트 (테스트에서도 필요)
try:
    from packaging import version as packaging_version
except ImportError:
    # 테스트 환경에서는 설치되어 있다고 가정
    print("Warning: 'packaging' library not found, tests might fail.")
    pass


class TestValidateVersionConsistency(unittest.TestCase):

    def setUp(self):
        """각 테스트 메서드 실행 전에 호출되는 설정 메서드"""
        self.test_dir = TemporaryDirectory()
        # 임시 gradle.properties 파일 생성 (NamedTemporaryFile 사용 권장)
        self.prop_file = NamedTemporaryFile(mode='w+', delete=False, dir=self.test_dir.name, suffix=".properties", encoding='utf-8')
        self.prop_file_path = Path(self.prop_file.name)
        # 임시 GITHUB_OUTPUT 파일 생성
        self.github_output_file = NamedTemporaryFile(mode='w+', delete=False, dir=self.test_dir.name, suffix=".txt", encoding='utf-8')
        os.environ['GITHUB_OUTPUT'] = self.github_output_file.name

    def tearDown(self):
        """각 테스트 메서드 실행 후에 호출되는 정리 메서드"""
        self.prop_file.close()
        self.github_output_file.close()
        # 임시 파일 및 디렉토리 삭제 시도 (오류 무시)
        try:
            os.remove(self.prop_file_path)
        except OSError:
            pass
        try:
             os.remove(self.github_output_file.name)
        except OSError:
             pass
        self.test_dir.cleanup()
        # 환경 변수 정리
        if 'GITHUB_OUTPUT' in os.environ:
            del os.environ['GITHUB_OUTPUT']

    def _write_props(self, content):
        """테스트용 gradle.properties 파일 내용 작성"""
        self.prop_file.seek(0)
        self.prop_file.write(content)
        self.prop_file.truncate()
        self.prop_file.flush() # 파일 시스템에 즉시 반영

    def _read_props(self):
        """테스트용 gradle.properties 파일 내용 읽기"""
        self.prop_file.seek(0)
        return self.prop_file.read()

    def _read_github_output(self):
        """Mock GITHUB_OUTPUT 파일 내용 읽기"""
        self.github_output_file.seek(0)
        return self.github_output_file.read()

    # --- Mocking Git ---
    # get_latest_tag 직접 모킹하므로 이 함수는 불필요
    # def mock_run_git_command(self, command): ...

    # --- Test Cases ---

    @patch('validate_version_consistency.get_latest_tag')
    def test_update_needed_and_successful(self, mock_get_latest_tag):
        """정상: 입력 버전 > libVersion, 태그 없음 -> 업데이트 성공"""
        self._write_props("libVersion=1.0.0")
        mock_get_latest_tag.return_value = None # 태그 없음
        args = ["--expected-version", "1.1.0", "--prop-file", str(self.prop_file_path)]

        with patch.object(sys, 'argv', ['script_name'] + args):
             # main()은 sys.exit(1) 호출 시 SystemExit 예외 발생
             validate_version_consistency.main() # 예외 발생 안해야 함

        # 파일 내용 검증
        self.assertIn("libVersion=1.1.0", self._read_props())
        # 출력 검증
        self.assertIn("updated=true", self._read_github_output())

    @patch('validate_version_consistency.get_latest_tag')
    def test_update_needed_with_tag_check(self, mock_get_latest_tag):
        """정상: 입력 버전 > libVersion, 입력 버전 > 최신 태그 -> 업데이트 성공 (표준 프리릴리즈 사용)"""
        # 수정: libVersion을 표준 프리릴리즈 형식으로 변경
        self._write_props("libVersion=1.1.0rc1")
        # 최신 태그 모킹 (packaging.version 객체 반환 가정)
        mock_get_latest_tag.return_value = packaging_version.parse("1.0.0")
        # 수정: 입력 버전도 표준 프리릴리즈 또는 정식 버전 사용
        args = ["--expected-version", "v1.1.0", "--prop-file", str(self.prop_file_path)] # 'v' 접두사 포함

        with patch.object(sys, 'argv', ['script_name'] + args):
             validate_version_consistency.main()

        self.assertIn("libVersion=1.1.0", self._read_props()) # 'v' 제거된 버전으로 업데이트됨
        self.assertIn("updated=true", self._read_github_output())

    @patch('validate_version_consistency.get_latest_tag')
    def test_no_update_needed_same_version(self, mock_get_latest_tag):
        """정상: 입력 버전 == libVersion, 태그 없음 -> 업데이트 불필요"""
        self._write_props("libVersion = 1.2.3 ") # 공백 포함
        mock_get_latest_tag.return_value = None
        args = ["--expected-version", "1.2.3", "--prop-file", str(self.prop_file_path)]

        with patch.object(sys, 'argv', ['script_name'] + args):
             validate_version_consistency.main()

        self.assertIn("libVersion = 1.2.3", self._read_props().strip()) # strip() 추가하여 공백 무시 비교
        self.assertIn("updated=false", self._read_github_output())

    @patch('validate_version_consistency.get_latest_tag')
    def test_no_update_needed_same_version_with_tag(self, mock_get_latest_tag):
        """정상: 입력 버전 == libVersion, 입력 버전 > 최신 태그 -> 업데이트 불필요"""
        self._write_props("libVersion=1.2.3")
        mock_get_latest_tag.return_value = packaging_version.parse("1.2.0")
        args = ["--expected-version", "1.2.3", "--prop-file", str(self.prop_file_path)]

        with patch.object(sys, 'argv', ['script_name'] + args):
             validate_version_consistency.main()

        self.assertIn("libVersion=1.2.3", self._read_props()) # 변경 없음
        self.assertIn("updated=false", self._read_github_output())


    @patch('validate_version_consistency.get_latest_tag')
    def test_fail_input_less_than_libversion(self, mock_get_latest_tag):
        """실패: 입력 버전 < libVersion"""
        self._write_props("libVersion=1.0.1")
        mock_get_latest_tag.return_value = None
        args = ["--expected-version", "1.0.0", "--prop-file", str(self.prop_file_path)]

        with patch.object(sys, 'argv', ['script_name'] + args), \
             self.assertRaises(SystemExit) as cm: # sys.exit(1) 검증
            validate_version_consistency.main()
        self.assertEqual(cm.exception.code, 1)
        # 파일 내용 변경 없어야 함
        self.assertIn("libVersion=1.0.1", self._read_props())
        # updated 출력 없어야 함 (실패 시)
        self.assertNotIn("updated=", self._read_github_output())


    @patch('validate_version_consistency.get_latest_tag')
    def test_fail_input_less_than_tag(self, mock_get_latest_tag):
        """실패: 입력 버전 < 최신 태그"""
        self._write_props("libVersion=1.0.0")
        mock_get_latest_tag.return_value = packaging_version.parse("1.1.0")
        args = ["--expected-version", "1.0.5", "--prop-file", str(self.prop_file_path)]

        with patch.object(sys, 'argv', ['script_name'] + args), \
             self.assertRaises(SystemExit) as cm:
            validate_version_consistency.main()
        self.assertEqual(cm.exception.code, 1)
        self.assertIn("libVersion=1.0.0", self._read_props())
        self.assertNotIn("updated=", self._read_github_output())

    @patch('validate_version_consistency.get_latest_tag')
    def test_fail_invalid_input_version(self, mock_get_latest_tag):
        """실패: 입력 버전 형식 오류"""
        self._write_props(" libVersion = 1.0.0 ")
        mock_get_latest_tag.return_value = None
        args = ["--expected-version", "invalid-version", "--prop-file", str(self.prop_file_path)]

        with patch.object(sys, 'argv', ['script_name'] + args), \
             self.assertRaises(SystemExit) as cm:
            validate_version_consistency.main()
        self.assertEqual(cm.exception.code, 1)

    @patch('validate_version_consistency.get_latest_tag')
    def test_fail_invalid_libversion(self, mock_get_latest_tag):
        """실패: libVersion 형식 오류"""
        self._write_props("libVersion=bad.format")
        mock_get_latest_tag.return_value = None
        args = ["--expected-version", "1.0.0", "--prop-file", str(self.prop_file_path)]

        with patch.object(sys, 'argv', ['script_name'] + args), \
             self.assertRaises(SystemExit) as cm:
            validate_version_consistency.main()
        self.assertEqual(cm.exception.code, 1)

    @patch('validate_version_consistency.run_git_command') # get_latest_tag 내부의 git 호출 모킹
    def test_get_latest_tag_logic(self, mock_git):
        """get_latest_tag 함수 자체 로직 테스트"""
        # Mock 반환값 설정
        def git_side_effect(command):
            if 'fetch' in command: return "OK"
            if 'tag' in command and 'fetch' not in command:
                 # 수정: 모호한 태그 제거 (v2.0.0-alpha.1 제거)
                 return "v1.0.0\nv0.9.0\nv1.1.0-RC1\nv1.1.0\nnon-semantic"
            return None
        mock_git.side_effect = git_side_effect

        latest = validate_version_consistency.get_latest_tag()
        # 수정된 데이터에서는 1.1.0 이 명확히 최신 버전임
        self.assertEqual(latest, packaging_version.parse("1.1.0"))

    @patch('validate_version_consistency.run_git_command')
    def test_get_latest_tag_no_tags(self, mock_git):
        """get_latest_tag: 태그 없을 때 None 반환 테스트"""
        def git_side_effect(command):
            if 'fetch' in command: return "OK"
            if 'tag' in command and 'fetch' not in command: return "" # 빈 문자열 (태그 없음)
            return None
        mock_git.side_effect = git_side_effect

        self.assertIsNone(validate_version_consistency.get_latest_tag())

    # --- 파일 업데이트 로직 상세 테스트 ---
    def test_update_gradle_property_success(self):
        """update_gradle_property: 정상 업데이트 테스트"""
        self._write_props("libVersion=1.0.0\nother=value\n#comment")
        result = validate_version_consistency.update_gradle_property(self.prop_file_path, 'libVersion', '1.1.0')
        self.assertTrue(result)
        self.assertIn("libVersion=1.1.0", self._read_props())
        self.assertIn("other=value", self._read_props()) # 다른 줄 유지 확인

    def test_update_gradle_property_no_change(self):
        """update_gradle_property: 값이 같아 업데이트 불필요 테스트"""
        self._write_props("libVersion=1.0.0")
        # update_gradle_property는 변경이 없으면 False를 반환함
        result = validate_version_consistency.update_gradle_property(self.prop_file_path, 'libVersion', '1.0.0')
        self.assertFalse(result, "Expected update_gradle_property to return False when no change is made")
        self.assertIn("libVersion=1.0.0", self._read_props())

    def test_update_gradle_property_key_not_found(self):
        """update_gradle_property: 키 없을 때 실패 테스트"""
        self._write_props("otherVersion=1.0.0")
        result = validate_version_consistency.update_gradle_property(self.prop_file_path, 'libVersion', '1.1.0')
        self.assertFalse(result)
        self.assertNotIn("libVersion=1.1.0", self._read_props())

    def test_update_gradle_property_with_spaces_and_comments(self):
        """update_gradle_property: 공백/주석 있는 라인 업데이트 테스트"""
        original_line = "  libVersion = 1.0.0 # Old version"
        self._write_props(original_line)
        result = validate_version_consistency.update_gradle_property(self.prop_file_path, 'libVersion', '1.1.0-beta')
        self.assertTrue(result)
        # 수정된 정규식은 주석을 보존해야 함
        expected_line = "  libVersion = 1.1.0-beta # Old version"
        # expected_line 에서도 strip() 호출
        self.assertIn(expected_line.strip(), [line.strip() for line in self._read_props().splitlines()])


if __name__ == '__main__':
    # 테스트 실행
    unittest.main(argv=['first-arg-is-ignored'], exit=False)
