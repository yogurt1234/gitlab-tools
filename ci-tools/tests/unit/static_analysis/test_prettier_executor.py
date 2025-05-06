# tests/unit/test_prettier_executor.py

import subprocess
import pytest
from pathlib import Path
import config
from modules.static_analysis.prettier_executor import PrettierExecutor


@pytest.fixture(autouse=True)
def tmp_gitlab_dir(monkeypatch, tmp_path):
    # テスト用のプロジェクトルートを設定
    monkeypatch.setattr(config, 'PROJECT_BASE_DIR', str(tmp_path), raising=False)
    return tmp_path


@pytest.fixture
def executor(tmp_gitlab_dir):
    # src_dir をテスト用ディレクトリとし、コマンドはダミー
    return PrettierExecutor(prettier_cmd=['prettier'], src_dir=str(tmp_gitlab_dir))


def test_execute_empty_list(executor):
    # target_files が空なら空リストを返す
    assert executor.execute([]) == {'files': []}


def test_execute_no_existing_files(executor, tmp_gitlab_dir, capsys):
    # 存在しないファイル指定時は空リストとメッセージ
    result = executor.execute(['nofile.js'])
    captured = capsys.readouterr()
    assert '存在しません' in captured.out
    assert result == {'files': []}


def test_run_prettier_error(monkeypatch, executor, tmp_gitlab_dir):
    # テスト用ファイルを作成
    f = tmp_gitlab_dir / 'a.js'
    f.write_text('console.log(1);')
    # モック subprocess.run がエラーコード >1 を返す

    def fake_run(cmd, cwd, capture_output, text, check, shell):
        return subprocess.CompletedProcess(cmd, returncode=2, stdout='', stderr='err')
    monkeypatch.setattr(subprocess, 'run', fake_run)
    with pytest.raises(subprocess.CalledProcessError):
        executor.execute(['a.js'])


def test_execute_happy_path(monkeypatch, executor, tmp_gitlab_dir):
    # テスト用ファイルを作成
    f1 = tmp_gitlab_dir / 'file1.js'
    f1.write_text('x')
    f2 = tmp_gitlab_dir / 'file2.ts'
    f2.write_text('y')
    # モック subprocess.run で list-different出力を返す
    output = 'file1.js\nfile2.ts'

    def fake_run(cmd, cwd, capture_output, text, check, shell):
        return subprocess.CompletedProcess(cmd, returncode=1, stdout=output, stderr='')
    monkeypatch.setattr(subprocess, 'run', fake_run)

    result = executor.execute(['file1.js', 'file2.ts'], )
    files = result['files']
    # ファイルごとの violation オブジェクトが含まれる
    paths = [Path(f['filename']) for f in files]
    assert Path(str(tmp_gitlab_dir.resolve() / 'file1.js')) in paths
    assert Path(str(tmp_gitlab_dir.resolve() / 'file2.ts')) in paths
    # violations フィールド構造
    for entry in files:
        assert isinstance(entry['violations'], list)
        assert entry['violations'][0]['description'].startswith('[warn]')


def test_summarize_none(executor):
    # 空リストなら None を返す
    assert executor.summarize({'files': []}) is None


def test_summarize_message(executor, tmp_gitlab_dir):
    # 出力済み violations を持つファイルでメッセージ生成を検証
    abs1 = str((tmp_gitlab_dir / 'a.js').resolve())
    analysis = {
        'files': [
            {'filename': abs1, 'violations': [{'beginline': 1, 'description': 'd', 'externalInfoUrl': 'u'}]}
        ]
    }
    msg = executor.summarize(analysis)
    assert 'Prettier フォーマット違反' in msg
    # ファイル名が相対パスで含まれていること
    rel = Path(abs1).relative_to(Path(str(tmp_gitlab_dir))).as_posix()
    assert f'`{rel}`' in msg
