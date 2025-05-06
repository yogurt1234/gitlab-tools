import os
from pathlib import Path
import shutil
import subprocess
from typing import List, Dict, Optional
from modules.static_analysis.abstract_static_analyzer import AbstractStaticAnalyzer
import config


class PrettierExecutor(AbstractStaticAnalyzer):

    def __init__(self, prettier_cmd: List[str] = None, src_dir: str = ""):
        self.prettier_cmd = prettier_cmd or ["npx", "prettier"]
        self.src_dir = Path(src_dir).resolve()

    def execute(self, target_files: List[str]) -> Dict[str, List[Dict]]:
        if not target_files:
            return {"files": []}

        files = self._filter_and_resolve_files(target_files)
        if not files:
            print("Prettier: 実行対象ファイルが存在しません。")
            return {"files": []}

        out = self._run_prettier(files)
        print("prettier_output")
        print(out)
        return {"files": self._parse_output(out)}

    def summarize(self, analysis_output: dict) -> Optional[str]:
        files = analysis_output.get("files", [])
        if not files:
            return None  # フォーマット違反なし
        # ファイル数やパスを読み取ってメッセージを作成
        file_list = "\n".join(f"- `{Path(f['filename']).relative_to(self.src_dir)}`"
                              for f in files)
        return (
            "::bell:: **Prettier フォーマット違反** が検出されました。\n"
            "以下のファイルに整形が必要です：\n"
            f"{file_list}\n\n"
            "ローカルで `npx prettier --write` を実行してから再度 push してください。"
        )

    def _filter_and_resolve_files(self, target_files: list[str]) -> list[str]:
        """存在し、かつ self.src_dir のサブパスであるファイルだけを抽出し、相対パス化する"""
        resolved_files = []
        for relative_path in target_files:
            # PROJECT_BASE_DIR から絶対パス化
            abs_path = os.path.abspath(os.path.join(config.PROJECT_BASE_DIR, relative_path))

            if not os.path.exists(abs_path):
                print(f"Pretter: ファイルが存在しません: {abs_path}")
                continue

            # self.src_dir と commonpath を取ってサブパスか判定
            try:
                common = os.path.commonpath([self.src_dir, abs_path])
            except ValueError:
                # パスがまったく異なるドライブ等にある場合
                print(f"Pretter: スキップ（異なるドライブ）: {abs_path}")
                continue

            if common != str(self.src_dir):
                # self.src_dir の外側のファイルは無視
                print(f"Pretter: プロジェクト外のファイルをスキップ: {abs_path}")
                continue

            # 問題なければ、cwd(self.src_dir) からの相対パスにして追加
            rel = os.path.relpath(abs_path, start=self.src_dir)
            resolved_files.append(rel)

        return resolved_files

    def _run_prettier(self, files: List[str]) -> str:
        # ── Windows で npx.cmd を見つける ──
        exe = self.prettier_cmd[0]
        found = shutil.which(exe)
        # found が None の場合は元の exe を使い、あればフルパスを利用
        cmd0 = found or exe

        # --list-different で unformatted ファイルだけを一行ずつ出力
        cmd = [cmd0, *self.prettier_cmd[1:], "--list-different", *files]
        result = subprocess.run(
            cmd,
            cwd=self.src_dir,
            capture_output=True,
            text=True,
            check=False,
            shell=False
        )
        # exit code 0: no diffs, 1: diffs found, else: error
        if result.returncode > 1:
            print(
                f"Prettier: 異常終了 (コード: {result.returncode})\n{result.stderr}")
            raise subprocess.CalledProcessError(
                result.returncode, result.args, result.stdout, result.stderr
            )
        return result.stdout or ""

    def _parse_output(self, out: str) -> List[Dict]:
        parsed = []
        for line in out.splitlines():
            fp = line.strip()
            # Path 結合して絶対化
            absf = Path(fp).resolve() if Path(
                fp).is_absolute() else (self.src_dir / fp).resolve()
            parsed.append({
                "filename": absf.as_posix(),
                "violations": [{
                    "beginline": 1,
                    "description": "[warn] Prettier format mismatch",
                    "externalInfoUrl": "formatter:prettier"
                }]
            })
        return parsed
