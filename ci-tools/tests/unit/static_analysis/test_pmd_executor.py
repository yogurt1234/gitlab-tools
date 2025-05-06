# tests/unit/test_pmd_executor.py

import os
import json
import subprocess
import pytest
import config
from modules.static_analysis.pmd_executor import PMDExecutor


@pytest.fixture(autouse=True)
def tmp_gitlab_dir(monkeypatch, tmp_path):
    # config に PROJECT_BASE_DIR が定義されていない場合でも追加できるように
    monkeypatch.setattr(config, "PROJECT_BASE_DIR", str(tmp_path), raising=False)
    return tmp_path


@pytest.fixture
def executor():
    return PMDExecutor(pmd_path="pmd")


# PMD 標準出力サンプルに合わせたテスト用データ
SAMPLE_PMD_OUTPUT = {
    "formatVersion": 0,
    "pmdVersion": "7.10.0",
    "timestamp": "2025-05-04T20:08:17.958+09:00",
    "files": [
        {
            "filename": "HelloWrold/src/main/java/helloworld/HelloWorld.java",
            "violations": [
                {
                    "beginline": 5,
                    "begincolumn": 20,
                    "endline": 5,
                    "endcolumn": 24,
                    "description": "Avoid unused private fields such as 'hoge'.",
                    "rule": "UnusedPrivateField",
                    "ruleset": "Best Practices",
                    "priority": 3,
                    "externalInfoUrl": "https://docs.pmd-code.org/pmd-doc-7.11.0/pmd_rules_java_bestpractices.html#unusedprivatefield"
                }
            ]
        }
    ],
    "suppressedViolations": [],
    "processingErrors": [],
    "configurationErrors": []
}


def test_execute_happy_path_full_output(monkeypatch, executor, tmp_gitlab_dir, tmp_path):
    # 準備：テスト用ファイルを配置
    f1 = tmp_gitlab_dir / "HelloWorld.java"
    f1.write_text("class HelloWorld {}")
    report_file = tmp_path / "report.json"

    # subprocess.run をモックしてサンプルJSONを書き込む
    captured = {}

    def fake_run(cmd, capture_output, text, check, shell):
        captured['cmd'] = cmd
        with open(report_file, 'w', encoding='utf-8') as wf:
            json.dump(SAMPLE_PMD_OUTPUT, wf)
        return subprocess.CompletedProcess(cmd, returncode=0, stdout="", stderr="")
    monkeypatch.setattr(subprocess, 'run', fake_run)

    # os.remove をモックして一時ファイルを残す
    monkeypatch.setattr(os, 'remove', lambda path: None)

    # 実行
    result = executor.execute(
        target_files=["HelloWorld.java"],
        report_file=str(report_file)
    )
    # ファイル名が含まれることをチェック
    filenames = [f["filename"] if isinstance(f, dict) else f for f in result.get('files', [])]
    assert "HelloWrold/src/main/java/helloworld/HelloWorld.java" in filenames


def test_execute_empty_list(executor):
    assert executor.execute([]) == {"files": []}


def test_execute_error_code(monkeypatch, executor, tmp_gitlab_dir, tmp_path):
    f = tmp_gitlab_dir / "X.java"
    f.write_text("class X {}")
    report_file = tmp_path / "report.json"
    report_file.write_text("{}")

    def fake_run(cmd, capture_output, text, check, shell):
        return subprocess.CompletedProcess(cmd, returncode=1, stdout="", stderr="err")
    monkeypatch.setattr(subprocess, 'run', fake_run)
    with pytest.raises(subprocess.CalledProcessError):
        executor.execute(["X.java"], report_file=str(report_file))


def test_execute_json_error(monkeypatch, executor, tmp_gitlab_dir, tmp_path):
    f = tmp_gitlab_dir / "Y.java"
    f.write_text("class Y {}")
    bad = tmp_path / "bad.json"
    bad.write_text("not json")

    def fake_run(cmd, capture_output, text, check, shell):
        return subprocess.CompletedProcess(cmd, returncode=0, stdout="", stderr="")
    monkeypatch.setattr(subprocess, 'run', fake_run)
    with pytest.raises(json.JSONDecodeError):
        executor.execute(["Y.java"], report_file=str(bad))


def test_summarize_returns_none(executor):
    assert executor.summarize({}) is None
