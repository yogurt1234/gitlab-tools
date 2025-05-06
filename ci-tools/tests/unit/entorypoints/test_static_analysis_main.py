# tests/unit/entorypoints/test_static_analysis_main.py

import sys
import argparse
import pytest
from types import SimpleNamespace

# モジュールのインポート
import config
import entrypoints.static_analysis_main as sam
from modules.static_analysis.pmd_executor import PMDExecutor
from modules.static_analysis.eslint_executor import ESLintExecutor
from modules.static_analysis.prettier_executor import PrettierExecutor
from diff_providers.diff_provider import GitLabDiffProvider, LocalDiffProvider
from notifiers.notifier import GitLabCommentNotifier, LocalResultNotifier


class TestParseArguments:
    def test_missing_analyzer_raises(self, monkeypatch):
        monkeypatch.setattr(sys, 'argv', ['prog'])
        with pytest.raises(SystemExit):
            sam._parse_arguments()

    @pytest.mark.parametrize('arg', ['pmd', 'eslint', 'prettier'])
    def test_valid_analyzer(self, monkeypatch, arg):
        monkeypatch.setattr(sys, 'argv', ['prog', '--analyzer', arg])
        ns = sam._parse_arguments()
        assert isinstance(ns, argparse.Namespace)
        assert ns.analyzer == arg


class TestPrepareEnvironment:
    def test_local_environment(self, monkeypatch):
        monkeypatch.delenv('CI', raising=False)
        provider, notifier = sam._prepare_environment()
        assert isinstance(provider, LocalDiffProvider)
        assert isinstance(notifier, LocalResultNotifier)

    def test_ci_environment(self, monkeypatch):
        # CI環境をシミュレート
        monkeypatch.setenv('CI', 'true')
        settings = {
            'CI_PROJECT_ID': '123',
            'CI_MERGE_REQUEST_IID': '456',
            'GITLAB_TOKEN': 'token',
            'CI_PROJECT_DIR': '/tmp/project',
        }
        for k, v in settings.items():
            monkeypatch.setenv(k, v)
        # config モジュールの属性に反映
        monkeypatch.setattr(config, 'GITLAB_PROJECT_ID', '123', raising=False)
        monkeypatch.setattr(config, 'GITLAB_MR_IID', '456', raising=False)
        monkeypatch.setattr(config, 'GITLAB_TOKEN', 'token', raising=False)
        monkeypatch.setattr(config, 'PROJECT_BASE_DIR',
                            '/tmp/project', raising=False)

        provider, notifier = sam._prepare_environment()
        assert isinstance(provider, GitLabDiffProvider)
        assert isinstance(notifier, GitLabCommentNotifier)


class TestSelectAnalyzer:
    @pytest.fixture(autouse=True)
    def set_project_dir(self, monkeypatch, tmp_path):
        monkeypatch.setenv('CI', 'true')
        monkeypatch.setattr(config, 'PROJECT_BASE_DIR',
                            str(tmp_path), raising=False)
        return tmp_path

    def test_select_pmd(self):
        analyzer, exts = sam._select_analyzer('pmd')
        assert isinstance(analyzer, PMDExecutor)
        assert exts == ('.java',)

    def test_select_eslint(self):
        analyzer, exts = sam._select_analyzer('eslint')
        assert isinstance(analyzer, ESLintExecutor)
        assert set(exts) == {'.js', '.ts', '.vue'}

    def test_select_prettier(self):
        analyzer, exts = sam._select_analyzer('prettier')
        assert isinstance(analyzer, PrettierExecutor)
        assert set(exts) == {'.js', '.ts', '.vue'}

    def test_select_invalid(self):
        with pytest.raises(ValueError):
            sam._select_analyzer('invalid')


class TestMainFunction:
    class DummyProcessor:
        def __init__(self):
            self.run_called = False

        def run(self):
            self.run_called = True

    @pytest.fixture(autouse=True)
    def stub_common(self, monkeypatch):
        # parse_args と prepare_environment をスタブ化
        ns = SimpleNamespace(analyzer='pmd')
        monkeypatch.setattr(sam, '_parse_arguments', lambda: ns)
        monkeypatch.setenv('CI', 'true')
        monkeypatch.setenv('CI_PROJECT_ID', '123')
        monkeypatch.setenv('CI_MERGE_REQUEST_IID', '456')
        monkeypatch.setenv('GITLAB_TOKEN', 'token')
        monkeypatch.setenv('CI_PROJECT_DIR', '/tmp/project')
        monkeypatch.setattr(sam, '_prepare_environment',
                            lambda: ('prov', 'notifier'))
        yield

    def test_main_success(self, monkeypatch):
        dummy = TestMainFunction.DummyProcessor()
        monkeypatch.setattr(sam, 'StaticAnalysisProcessor',
                            lambda *args, **kwargs: dummy)

        sam.static_analysis_main()
        assert dummy.run_called

    @pytest.mark.parametrize('exc, msg', [
        (ValueError('bad config'), '[設定エラー] bad config'),
        (OSError('fs fail'), '[システムエラー] fs fail'),
        (RuntimeError('oops'), '[実行時エラー] oops'),
    ])
    def test_main_error_paths(self, monkeypatch, capsys, exc, msg):
        monkeypatch.setattr(sam, '_select_analyzer',
                            lambda a: (_ for _ in ()).throw(exc))
        with pytest.raises(SystemExit) as se:
            sam.static_analysis_main()
        assert se.value.code == 1
        out = capsys.readouterr().out
        assert msg in out
