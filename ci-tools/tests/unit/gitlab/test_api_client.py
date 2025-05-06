# tests/unit/test_api_client.py
import pytest
import requests

from modules.gitlab.api_client import GitLabAPIClient


@pytest.fixture
def client():
    # テスト用に base_url を短くしています
    return GitLabAPIClient(
        project_id="proj123",
        mr_iid="mr456",
        token="tok789",
        base_url="https://git.example.com/api/v4"
    )


class DummyResponse:
    def __init__(self, status_code=200, json_data=None, text=""):
        self.status_code = status_code
        self._json = json_data or {}
        self.text = text

    def json(self):
        return self._json

    def raise_for_status(self):
        if self.status_code >= 400:
            raise requests.HTTPError(f"HTTP {self.status_code}")


def test_get_merge_request_diff_success(monkeypatch, client):
    # モック GET による正常系
    dummy = {"changes": [{"a": 1}, {"b": 2}]}

    def fake_get(url, headers):
        # URL とヘッダーが正しく組み立てられていることを確認
        assert url == "https://git.example.com/api/v4/projects/proj123/merge_requests/mr456/changes"
        assert headers == {"PRIVATE-TOKEN": "tok789"}
        return DummyResponse(status_code=200, json_data=dummy)
    monkeypatch.setattr(requests, "get", fake_get)

    result = client.get_merge_request_diff()
    assert result == dummy


def test_get_merge_request_diff_http_error(monkeypatch, client):
    # モック GET で 404 を返し、HTTPError が伝播すること
    def fake_get(url, headers):
        return DummyResponse(status_code=404)
    monkeypatch.setattr(requests, "get", fake_get)

    with pytest.raises(requests.HTTPError):
        client.get_merge_request_diff()


@pytest.mark.parametrize("code", [200, 201])
def test_post_comment_success(monkeypatch, client, capsys, code):
    # モック POST による success
    payload_record = {}
    data = {"discussion": "ok"}

    def fake_post(url, headers, json):
        # URL とヘッダー・ペイロードをチェック
        assert url == "https://git.example.com/api/v4/projects/proj123/merge_requests/mr456/discussions"
        assert headers == {"PRIVATE-TOKEN": "tok789"}
        payload_record.update(json)
        return DummyResponse(status_code=code, json_data=data)
    monkeypatch.setattr(requests, "post", fake_post)

    pos = {"position": "x"}
    resp = client.post_comment("hello", pos)
    assert resp == data
    # 失敗メッセージは出力されない
    out = capsys.readouterr().out
    assert "失敗しました" not in out
    # ペイロード body と position が正しく渡されている
    assert payload_record["body"] == "hello"
    assert payload_record["position"] == pos


def test_post_comment_failure(monkeypatch, client, capsys):
    # モック POST で 500 を返し、エラーメッセージが print されるが例外は投げない
    data = {"error": "bad"}

    def fake_post(url, headers, json):
        return DummyResponse(status_code=500, json_data=data)
    monkeypatch.setattr(requests, "post", fake_post)

    pos = {"position": "y"}
    resp = client.post_comment("oops", pos)
    # レスポンス JSON は返ってくる
    assert resp == data
    out = capsys.readouterr().out
    assert "oops" in out and "position" in out


def test_post_note_success(monkeypatch, client):
    # モック POST によるノート投稿
    note_body = "note text"
    returned = {"note": "created"}

    def fake_post(url, headers, json):
        # URL 構築確認
        expected = "https://git.example.com/api/v4/projects/proj123/merge_requests/mr456/notes"
        assert url == expected
        assert headers == {"PRIVATE-TOKEN": "tok789"}
        assert json == {"body": note_body}
        return DummyResponse(status_code=201, json_data=returned)
    monkeypatch.setattr(requests, "post", fake_post)

    resp = client.post_note(note_body)
    assert resp is None
