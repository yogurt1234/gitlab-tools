# tests/unit/test_notifier.py

import pytest
from notifiers.notifier import GitLabCommentNotifier, LocalResultNotifier


class DummyAPIClient:
    def __init__(self):
        self.notes = []
        self.comments = []

    def post_note(self, summary):
        self.notes.append(summary)

    def post_comment(self, comment, position):
        self.comments.append((comment, position))


@pytest.fixture
def dummy_api():
    return DummyAPIClient()


@pytest.fixture
def gl_notifier(dummy_api):
    return GitLabCommentNotifier(dummy_api)


@pytest.fixture
def local_notifier():
    return LocalResultNotifier()


class TestGitLabCommentNotifier:
    def test_notify_summary(self, gl_notifier, dummy_api):
        # 要約ありの場合、post_note が呼ばれる
        gl_notifier.notify([], summary="テスト要約")
        assert dummy_api.notes == ["テスト要約"]
        assert dummy_api.comments == []

    def test_notify_violations(self, gl_notifier, dummy_api):
        # 1件の違反通知シナリオ
        diff_content = {
            'base_sha': 'b1', 'start_sha': 's1', 'head_sha': 'h1',
            'p': {'old_path': 'old.java', 'new_path': 'new.java'}
        }
        violation = {'beginline': 7, 'description': '説明', 'externalInfoUrl': 'http://url'}
        gl_notifier.notify([(diff_content, violation, 'p')], summary=None)
        # post_comment が1回呼ばれる
        assert len(dummy_api.comments) == 1
        comment, position = dummy_api.comments[0]
        # position の内容検証
        expected_pos = {
            'base_sha': 'b1', 'start_sha': 's1', 'head_sha': 'h1',
            'old_path': 'old.java', 'new_path': 'new.java',
            'position_type': 'text', 'new_line': 7
        }
        assert position == expected_pos
        # コメント文にプレフィックスと詳細が含まれている
        assert '静的解析結果を確認してください' in comment
        assert '説明' in comment
        assert 'http://url' in comment


class TestLocalResultNotifier:
    def test_notify_empty(self, local_notifier, capsys):
        # 空リスト時は OK メッセージだけ
        local_notifier.notify([])
        out = capsys.readouterr().out.strip()
        assert out == "解析結果: OK"

    def test_notify_violations(self, local_notifier, capsys):
        # 1件の違反通知シナリオ
        diff_content = {}  # LocalResultNotifier では使われない
        violation = {
            'beginline': 3,
            'rule': 'ルール1',
            'description': '説明文',
            'externalInfoUrl': 'http://url'
        }
        local_notifier.notify([(diff_content, violation, 'ignored')])
        out_lines = capsys.readouterr().out.strip().splitlines()
        # ヘッダとデータ行の3行
        assert out_lines[0] == "解析結果:NG"
        assert out_lines[1] == "ROW,RULE,DESCRIPTION,URL"
        assert out_lines[2] == "3,ルール1,説明文,http://url"
