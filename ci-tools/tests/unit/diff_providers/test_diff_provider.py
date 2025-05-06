# tests/unit/diff_providers/test_diff_provider.py

import subprocess
import pytest

import config
from diff_providers.diff_provider import GitLabDiffProvider, LocalDiffProvider
import diff_providers.diff_provider as dp

# ダミー API クライアント


class DummyAPIClient:
    def __init__(self, diff_data):
        self.diff_data = diff_data
        self.called = False

    def get_merge_request_diff(self):
        self.called = True
        return self.diff_data

# ダミーパーサ


class DummyParser:
    def __init__(self):
        self.input = None

    def parse(self, diff):
        self.input = diff
        return {"parsed": diff}


def test_gitlab_diff_provider(monkeypatch):
    # GitLabDiffProvider は API 呼び出しとパースを行う
    dummy_diff = {"any": "data"}
    api = DummyAPIClient(dummy_diff)
    parser = DummyParser()
    # GitLabDiffParser をモックに置き換え
    monkeypatch.setattr(dp, 'GitLabDiffParser', lambda: parser)

    provider = GitLabDiffProvider(api, None)
    result = provider.get_diff()

    # API とパーサが正しく呼ばれる
    assert api.called, "APIクライアントの get_merge_request_diff が呼ばれる"
    assert parser.input == dummy_diff, "取得した生 diff がパーサに渡される"
    assert result == {"parsed": dummy_diff}, "パース結果が返る"


def test_local_diff_provider_no_option(monkeypatch):
    # GIT_DIFF_OPTION 未設定時
    parser = DummyParser()
    provider = LocalDiffProvider(parser)
    monkeypatch.setattr(config, 'GIT_DIFF_OPTION', '', raising=False)
    fake = subprocess.CompletedProcess(
        args=["git", "diff"], returncode=0, stdout="raw", stderr="")
    monkeypatch.setattr(subprocess, 'run', lambda *args, **kwargs: fake)

    result = provider.get_diff()
    assert parser.input == "raw", "stdout がパーサに渡される"
    assert result == {"parsed": "raw"}, "パース結果が返る"


def test_local_diff_provider_with_option(monkeypatch):
    # GIT_DIFF_OPTION 指定時
    parser = DummyParser()
    provider = LocalDiffProvider(parser)
    monkeypatch.setattr(config, 'GIT_DIFF_OPTION', '--staged', raising=False)

    called = {}

    def fake_run(cmd, *args, **kwargs):
        called['cmd'] = cmd
        return subprocess.CompletedProcess(cmd, returncode=0, stdout="", stderr="")
    monkeypatch.setattr(subprocess, 'run', fake_run)

    provider.get_diff()
    assert '--staged' in called['cmd'], "コマンドにオプションが含まれる"


def test_local_diff_provider_error(monkeypatch):
    # subprocess.run が例外を投げる
    parser = DummyParser()
    provider = LocalDiffProvider(parser)
    monkeypatch.setattr(config, 'GIT_DIFF_OPTION', '', raising=False)

    def fake_run(*args, **kwargs):
        raise subprocess.CalledProcessError(returncode=1, cmd=args[0])
    monkeypatch.setattr(subprocess, 'run', fake_run)

    with pytest.raises(subprocess.CalledProcessError):
        provider.get_diff()
