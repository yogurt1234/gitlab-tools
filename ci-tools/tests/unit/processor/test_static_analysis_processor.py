# tests/unit/test_static_analysis_processor.py

from pathlib import Path
import pytest
import config
from processors.static_analysis_processor import StaticAnalysisProcessor


class DummyDiffProvider:
    def __init__(self, diff):
        self._diff = diff

    def get_diff(self):
        return self._diff


class DummyExecutor:
    def __init__(self, execute_output, summary_output):
        self.execute_output = execute_output
        self.summary_output = summary_output
        self.execute_called = False
        self.summarize_called = False

    def execute(self, paths):
        self.execute_called = True
        self.paths = paths
        return self.execute_output

    def summarize(self, results):
        self.summarize_called = True
        self.results = results
        return self.summary_output


class DummyNotifier:
    def __init__(self):
        self.notify_called = False
        self.args = None

    def notify(self, violations, summary):
        self.notify_called = True
        self.args = (violations, summary)


@pytest.fixture(autouse=True)
def set_gitlab_dir(monkeypatch, tmp_path):
    # patch base_dir for relative conversion
    monkeypatch.setattr(config, 'PROJECT_BASE_DIR', str(tmp_path), raising=False)
    return tmp_path


@pytest.fixture
def processor_factory(tmp_path):
    def factory(diff, exec_out, summary_out, target_ext=None):
        diff_provider = DummyDiffProvider(diff)
        executor = DummyExecutor(exec_out, summary_out)
        notifier = DummyNotifier()
        return StaticAnalysisProcessor(diff_provider, notifier, executor, target_ext), executor, notifier
    return factory


def test_extract_target_paths_no_extension_filter(processor_factory):
    diff = {
        'file1.java': {'new_path': 'src/A.java'},
        'file2.txt': {'new_path': 'docs/readme.txt'},
        'base_sha': 'abc'
    }
    proc, _, _ = processor_factory(diff, {}, None)
    paths = proc._extract_target_paths(diff)
    assert 'src/A.java' in paths
    assert 'docs/readme.txt' in paths


def test_extract_target_paths_with_extension_filter(processor_factory):
    diff = {
        'f1': {'new_path': 'A.java'},
        'f2': {'new_path': 'B.py'}
    }
    proc, _, _ = processor_factory(diff, {}, None, target_ext=('.java',))
    paths = proc._extract_target_paths(diff)
    assert paths == ['A.java']


def test_convert_to_relative_path_success(processor_factory):
    # create dummy file path under tmp_path
    gitlab_dir = Path(config.PROJECT_BASE_DIR)
    file_path = gitlab_dir / 'dir' / 'f.txt'
    file_path.parent.mkdir()
    file_path.write_text('x')
    proc, _, _ = processor_factory({}, {}, None)
    rel = proc._convert_to_relative_path(str(file_path))
    assert rel == 'dir/f.txt'


def test_convert_to_relative_path_outside(processor_factory):
    # path outside base: should return None and print error
    proc, _, _ = processor_factory({}, {}, None)
    out = proc._convert_to_relative_path('/does/not/exist')
    assert out is None


def test_filter_violations_changed_lines(processor_factory):
    # prepare diff_content with changed_lines
    diff = {
        'a.js': {'changed_lines': {3, 5}}
    }
    # executor output: two violations
    base = str(Path(config.PROJECT_BASE_DIR) / 'a.js')
    analysis = {
        'files': [{'filename': base, 'violations': [
            {'beginline': 3, 'description': 'd1'},
            {'beginline': 7, 'description': 'd2'}
        ]}]
    }
    proc, _, _ = processor_factory(diff, analysis, None)
    violations = proc._filter_violations(diff, analysis)
    # only beginline 3 should match
    assert len(violations) == 1
    diff_c, viol, path = violations[0]
    assert viol['description'] == 'd1'
    assert path == 'a.js'


def test_filter_violations_prettier_warning(processor_factory):
    diff = {'x': {'changed_lines': set()}}
    abs_path = str(Path(config.PROJECT_BASE_DIR) / 'x')
    analysis = {'files': [{'filename': abs_path, 'violations': [
        {'beginline': 1, 'description': '[warn] Prettier format error'}
    ]}]}
    proc, _, _ = processor_factory(diff, analysis, None)
    violations = proc._filter_violations(diff, analysis)
    assert len(violations) == 1
    _, viol, path = violations[0]
    assert viol['description'].startswith('[warn] Prettier')
    assert path == 'x'


def test_run_integration(processor_factory):
    # full run: ensure notify called with filtered violations and summary
    diff = {'f': [{'changed_lines': {2}}]}  # note diff value must be dict; fix
    # correct diff format
    diff = {'f': {'changed_lines': {2}}}
    base = str(Path(config.PROJECT_BASE_DIR) / 'f')
    analysis = {'files': [{'filename': base, 'violations': [
        {'beginline': 2, 'description': 'v'}
    ]}]}
    summary = 'sum'
    proc, executor, notifier = processor_factory(diff, analysis, summary)
    proc.run()
    # executor.execute and summarize called
    assert executor.execute_called
    assert executor.summarize_called
    # notifier.notify receives violations and summary
    assert notifier.notify_called
    vlist, s = notifier.args
    assert s == summary
    assert len(vlist) == 1
    _, viol, path = vlist[0]
    assert viol['description'] == 'v'
    assert path == 'f'
