# tests/integration/test_static_analysis_processor.py
from pathlib import Path
import pytest

import config
from processors.static_analysis_processor import StaticAnalysisProcessor
from modules.static_analysis.eslint_executor import ESLintExecutor
from modules.static_analysis.prettier_executor import PrettierExecutor
from modules.static_analysis.pmd_executor import PMDExecutor


class MockDiffProvider:
    def __init__(self, diff_dict):
        self.diff_dict = diff_dict

    def get_diff(self):
        print(self.diff_dict)
        return self.diff_dict


class CaptureNotifier:
    def __init__(self):
        self.notified = []

    def notify(self, violations, summary):
        # store both for assertions
        self.notified.append((violations, summary))


@pytest.mark.parametrize('executor_cls, pattern_extensions, data_dir', [
    (ESLintExecutor, ('.js', '.ts', '.vue'), Path(__file__).parent / 'data' / 'vue'),
    (PrettierExecutor, ('.js', '.ts', '.vue'), Path(__file__).parent / 'data' / 'vue'),
    (PMDExecutor, ('.java'), Path(__file__).parent / 'data' / 'java'),
])
def test_static_analysis_processor_eslint_prettier_integration(tmp_path, executor_cls, pattern_extensions, data_dir, monkeypatch):
    # データディレクトリ
    monkeypatch.setenv('PROJECT_BASE_DIR', str(data_dir))
    monkeypatch.setattr(config, 'PROJECT_BASE_DIR', str(data_dir))

    # 用意した Vue データフォルダ内のファイルすべてをdiffとして返す
    diff = {}
    # include base_sha fields to be skipped
    diff['base_sha'] = 'sha1'
    diff['start_sha'] = 'sha0'
    diff['head_sha'] = 'sha2'
    # scan files with given extensions
    for path in data_dir.rglob('*'):
        # skip node_modules directory
        if 'node_modules' in path.parts:
            continue
        if path.suffix in pattern_extensions:
            rel = path.relative_to(data_dir).as_posix()
            # mark all lines as changed for simplicity
            total_lines = path.read_text(encoding='utf-8').splitlines()
            diff[rel] = {
                'new_path': rel,
                'changed_lines': set(range(1, len(total_lines) + 1)),
            }
    diff_provider = MockDiffProvider(diff)
    notifier = CaptureNotifier()

    # create executor pointing to DATA_DIR
    if executor_cls is ESLintExecutor:
        executor = executor_cls(eslint_cmd=['npx', 'eslint'], src_dir=data_dir)
    elif executor_cls is PrettierExecutor:
        executor = executor_cls(prettier_cmd=['npx', 'prettier'], src_dir=data_dir)
    else:
        executor = executor_cls(config.PMD_PATH)

    # instantiate processor
    processor = StaticAnalysisProcessor(
        diff_provider=diff_provider,
        result_notifier=notifier,
        static_executor=executor,
        target_extensions=None
    )
    # run analysis
    processor.run()
    # assert notifier got called
    assert notifier.notified, 'No notifications were sent'
    # violations should be list of tuples
    violations, summary = notifier.notified[0]

    # summary may be None (e.g. Prettier), or a dict for ESLint
    assert isinstance(violations, list)

    print("violations")
    print(violations)
    # ESLintExecutor は summary が dict で files キーを含む
    if executor_cls is ESLintExecutor:
        assert summary is None
    elif executor_cls is PMDExecutor:
        assert summary is None
    else:
        assert summary is not None
