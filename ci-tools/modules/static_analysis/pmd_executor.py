from typing import Optional
import config
import os
from modules.static_analysis.abstract_static_analyzer import AbstractStaticAnalyzer
import subprocess
import json
import tempfile


class PMDExecutor(AbstractStaticAnalyzer):
    def __init__(self, pmd_path: str = r"pmd"):
        self.pmd_path = pmd_path

    def execute(self, target_files: list[str], report_file: str = "pmd_report.json") -> dict:
        if not target_files:
            return {"files": []}

        # コマンドライン引数で大量のファイルパスを渡すとエラーになる可能性があるため、
        # 一時ファイルに絶対パスを出力してパラメタに渡す
        # 削除されたファイルも差分としてでるので存在することを条件に入れる
        abs_target_files = []
        for relative_path in target_files:
            abs_path = os.path.join(config.PROJECT_BASE_DIR, relative_path)
            if os.path.exists(abs_path):
                abs_target_files.append(str(abs_path))

        with tempfile.NamedTemporaryFile(mode='w+', delete=False, suffix='.txt') as temp_file:
            for file_path in abs_target_files:
                temp_file.write(file_path + "\n")
            temp_file_path = temp_file.name

        command = [
            self.pmd_path,
            "check",
            "--file-list", temp_file_path,
            "-R", r"rulesets/java/quickstart.xml",
            "-f", "json",
            "-r", report_file
        ]

        try:
            result = subprocess.run(
                command,
                capture_output=True,
                text=True,
                check=False,
                shell=False
            )

            if result.returncode not in (0, 4):
                print("PMD の実行中に予期せぬエラーが発生しました:")
                print(result.stderr)
                raise subprocess.CalledProcessError(
                    result.returncode, command, result.stdout, result.stderr)

            with open(report_file, 'r', encoding='utf-8') as f:
                return json.load(f)

        finally:
            # 一時ファイル削除
            if os.path.exists(temp_file_path):
                os.remove(temp_file_path)

    def summarize(self, analysis_output: dict) -> Optional[str]:
        pass
