import os
import json
import shutil
import subprocess
from typing import Optional
from modules.static_analysis.abstract_static_analyzer import AbstractStaticAnalyzer
import config


class ESLintExecutor(AbstractStaticAnalyzer):
    def __init__(self, eslint_cmd: list[str] = None, src_dir: str = ""):
        """
        :param eslint_cmd: ESLint 実行コマンド（例: ["npx", "eslint"]）
        :param src_dir: ESLint 実行ディレクトリ（設定ファイルの存在場所）
        """
        self.eslint_cmd = eslint_cmd or ["npx", "eslint"]
        self.src_dir = src_dir

    def execute(self, target_files: list[str]) -> dict:
        if not target_files:
            return {"files": []}

        relative_target_files = self._filter_and_resolve_files(target_files)
        if not relative_target_files:
            print("ESLint: 実行対象ファイルが存在しません。")
            return {"files": []}

        eslint_output = self._run_eslint(relative_target_files)
        print(eslint_output)
        return {"files": self._parse_output(eslint_output)}

    def summarize(self, analysis_output: dict) -> Optional[str]:
        pass

    def _filter_and_resolve_files(self, target_files: list[str]) -> list[str]:
        """存在し、かつ self.src_dir のサブパスであるファイルだけを抽出し、相対パス化する"""
        resolved_files = []
        for relative_path in target_files:
            # PROJECT_BASE_DIR から絶対パス化
            abs_path = os.path.abspath(os.path.join(config.PROJECT_BASE_DIR, relative_path))

            if not os.path.exists(abs_path):
                print(f"ESLint: ファイルが存在しません: {abs_path}")
                continue

            # self.src_dir と commonpath を取ってサブパスか判定
            try:
                common = os.path.commonpath([self.src_dir, abs_path])
            except ValueError:
                # パスがまったく異なるドライブ等にある場合
                print(f"ESLint: スキップ（異なるドライブ）: {abs_path}")
                continue

            if common != str(self.src_dir):
                # self.src_dir の外側のファイルは無視
                print(f"ESLint: プロジェクト外のファイルをスキップ: {abs_path}")
                continue

            # 問題なければ、cwd(self.src_dir) からの相対パスにして追加
            rel = os.path.relpath(abs_path, start=self.src_dir)
            resolved_files.append(rel)

        return resolved_files

    def _run_eslint(self, files: list[str]) -> list[dict]:
        """ESLintを実行し、JSON出力を返す"""
        try:
            # ── Windows で npx.cmd を見つける ──
            exe = self.eslint_cmd[0]
            found = shutil.which(exe)
            # found が None の場合は元の exe を使い、あればフルパスを利用
            cmd0 = found or exe

            # 完成したコマンドリスト
            cmd = [cmd0, *self.eslint_cmd[1:], *files, "-f", "json"]

            result = subprocess.run(
                cmd,
                cwd=self.src_dir,
                capture_output=True,
                text=True,
                check=False
            )

            if result.returncode not in (0, 1):
                print(
                    f"ESLint: 異常終了 (コード: {result.returncode})\n{result.stderr}")
                raise subprocess.CalledProcessError(
                    result.returncode, result.args, result.stdout, result.stderr
                )
            # for debug
            return json.loads(result.stdout)

        except (subprocess.CalledProcessError, json.JSONDecodeError) as e:
            print(f"ESLint 実行エラー: {str(e)}")
            raise

    def _parse_output(self, eslint_output: list[dict]) -> list[dict]:
        parsed_files = []
        for entry in eslint_output:
            # ESLintのfilePathがすでに絶対パスである場合に備えてnormalize
            raw_file_path = entry.get("filePath", "")
            abs_file_path = (
                raw_file_path
                if os.path.isabs(raw_file_path)
                else os.path.abspath(os.path.join(self.src_dir, raw_file_path))
            )

            file_entry = {
                "filename": abs_file_path,
                "violations": [
                    {
                        "beginline": msg.get("line", 0),
                        "description": f"[{'error' if msg.get('severity', 1) == 2 else 'warn'}] {msg.get('message', '')}",
                        "externalInfoUrl": "ruleId:" + (msg.get("ruleId") or "")
                    }
                    for msg in entry.get("messages", [])
                ]
            }
            parsed_files.append(file_entry)
        return parsed_files
