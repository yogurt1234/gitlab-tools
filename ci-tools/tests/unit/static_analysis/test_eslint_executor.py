# tests/unit/test_eslint_executor.py

import json
import subprocess
import pytest
from pathlib import Path
import config
from modules.static_analysis.eslint_executor import ESLintExecutor


@pytest.fixture(autouse=True)
def tmp_gitlab_dir(monkeypatch, tmp_path):
    # config に PROJECT_BASE_DIR が定義されていない場合でも追加できるように
    monkeypatch.setattr(config, "PROJECT_BASE_DIR", str(tmp_path), raising=False)
    return tmp_path


@pytest.fixture
def executor(tmp_gitlab_dir):
    # ESLint コマンドはダミー、ソースディレクトリはテスト用ディレクトリ
    return ESLintExecutor(eslint_cmd=["eslint"], src_dir=str(tmp_gitlab_dir))


def test_execute_empty_list(executor):
    """空の target_files では即座に空の結果を返す"""
    assert executor.execute([]) == {"files": []}


def test_execute_no_existing_files(executor, capsys):
    """存在しないファイルだけ渡すと警告を出力して空の結果"""
    result = executor.execute(["nofile.js"])
    out = capsys.readouterr().out
    assert "実行対象ファイルが存在しません" in out
    assert result == {"files": []}


def test_filter_and_resolve_files(tmp_gitlab_dir, executor, capsys):
    """存在するファイルだけを相対パス化して返す"""
    # 1) 既存ファイル
    f = tmp_gitlab_dir / "a.js"
    f.write_text("console.log(1);")
    # 2) 存在しないファイル
    tmp_gitlab_dir / "b.js"
    lst = executor._filter_and_resolve_files(["a.js", "b.js"])
    out = capsys.readouterr().out
    # 存在しない b.js について警告
    assert "ファイルが存在しません" in out
    # 結果リストには相対パス 'a.js' だけ
    assert lst == ["a.js"]


def test_run_eslint_error(monkeypatch, executor, tmp_gitlab_dir):
    """ESLint の returncode が 0,1 以外なら例外を投げる"""
    f = tmp_gitlab_dir / "a.js"
    f.write_text("x")
    fake = subprocess.CompletedProcess(args=["eslint"], returncode=2, stdout="", stderr="err")
    monkeypatch.setattr(subprocess, "run", lambda *args, **kw: fake)
    with pytest.raises(subprocess.CalledProcessError):
        executor.execute(["a.js"])


def test_parse_and_execute_happy_path(monkeypatch, executor, tmp_gitlab_dir):
    """正常系：ESLint JSON 出力を正しくパースして返す"""
    # 2 つのファイルを作成
    f1 = tmp_gitlab_dir / "one.js"
    f1.write_text("x")
    f2 = tmp_gitlab_dir / "two.ts"
    f2.write_text("y")
    # モック JSON 出力
    sample_output = [
        {
            "filePath": str(f1.resolve()),
            "messages": [
                {"line": 3, "message": "foo", "severity": 1, "ruleId": "r1"}
            ]
        },
        {
            "filePath": "relative/two.ts",
            "messages": [
                {"line": 5, "message": "bar", "severity": 2, "ruleId": None}
            ]
        }
    ]
    fake = subprocess.CompletedProcess(
        args=["eslint"], returncode=1, stdout=json.dumps(sample_output), stderr=""
    )
    monkeypatch.setattr(subprocess, "run", lambda *args, **kw: fake)

    result = executor.execute(["one.js", "two.ts"])
    files = result["files"]
    # 結果件数
    assert len(files) == 2

    # 1st entry: severity 1 → "[warn]"
    e1 = next(e for e in files if Path(e["filename"]) == f1.resolve())
    v1 = e1["violations"][0]
    assert v1["beginline"] == 3
    assert v1["description"].startswith("[warn] foo")
    assert v1["externalInfoUrl"] == "ruleId:r1"

    # 2nd entry: severity 2 → "[error]"
    abs2 = (tmp_gitlab_dir / "relative/two.ts").resolve()
    e2 = next(e for e in files if Path(e["filename"]) == abs2)
    v2 = e2["violations"][0]
    assert v2["beginline"] == 5
    assert v2["description"].startswith("[error] bar")
    assert v2["externalInfoUrl"] == "ruleId:"


def test_summarize_returns_none(executor):
    """summarize は未実装なので None を返す"""
    assert executor.summarize({"files": []}) is None
