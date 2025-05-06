import config
from typing import Optional, List, Dict, Any, Tuple
from pathlib import Path
from modules.static_analysis.abstract_static_analyzer import AbstractStaticAnalyzer
from diff_providers.diff_provider import DiffProvider
from notifiers.notifier import ResultNotifyer


class StaticAnalysisProcessor:
    def __init__(self,
                 diff_provider: DiffProvider,
                 result_notifier: ResultNotifyer,
                 static_executor: AbstractStaticAnalyzer,
                 target_extensions: Optional[Tuple[str, ...]] = None):
        self.diff_provider = diff_provider
        self.result_notifier = result_notifier
        self.static_executor = static_executor
        self.target_extensions = target_extensions

    def run(self) -> None:
        """静的解析プロセスを実行します。"""
        # ファイルの差分を取得する
        diff_content = self.diff_provider.get_diff()
        # 対象の拡張子のファイルを抽出する
        target_paths = self._extract_target_paths(diff_content)
        # 解析を実行する
        analysis_results = self.static_executor.execute(target_paths)
        # 実行結果をまとめる場合はここで行う
        # prettierの場合は行が特定できないため違反であることだけを通知する
        summary = self.static_executor.summarize(analysis_results)

        # 取得した差分と違反箇所の突き合わせを行う
        violations = self._filter_violations(diff_content, analysis_results)
        # 通知する
        self.result_notifier.notify(violations, summary)

    def _extract_target_paths(self, diff_content: Dict[str, Any]) -> List[str]:
        """差分情報から解析対象のファイルパスを抽出します。"""
        reserved_keys = {"base_sha", "start_sha", "head_sha"}
        target_paths = []

        for key, value in diff_content.items():
            if key in reserved_keys:
                continue
            if isinstance(value, dict) and "new_path" in value:
                new_path = value["new_path"]
                if self.target_extensions:
                    if new_path.endswith(self.target_extensions):
                        target_paths.append(new_path)
                else:
                    target_paths.append(new_path)

        return target_paths

    def _filter_violations(self,
                           diff_content: Dict[str, Any],
                           analysis_output: Dict[str, Any]) -> List[Tuple[Dict[str, Any], Dict[str, Any], str]]:
        """差分情報と静的解析結果を突き合わせ、違反のみを抽出します。"""
        violations = []

        for file_result in analysis_output.get("files", []):
            abs_path = file_result.get("filename")
            relative_path = self._convert_to_relative_path(abs_path)
            if not relative_path:
                print(f"[警告] 相対パス変換失敗: {abs_path}")
                continue

            if relative_path not in diff_content:
                print(f"[警告] 差分に存在しないファイル: {relative_path}")
                continue

            changed_lines = diff_content[relative_path].get(
                'changed_lines', set())

            for violation in file_result.get("violations", []):
                beginline = violation.get("beginline", 0)

                # beginline==1 (Prettier特有)の場合は行チェックを無視して違反登録
                if beginline == 1 and violation.get("description", "").startswith("[warn] Prettier"):
                    violations.append((diff_content, violation, relative_path))
                # 通常の違反（行単位チェックあり）
                elif beginline in changed_lines:
                    print(
                        f"[警告] 変更行に違反が存在します: {relative_path} (行: {beginline})")
                    violations.append((diff_content, violation, relative_path))

        return violations

    def _convert_to_relative_path(self, abs_path: str) -> Optional[str]:
        """絶対パスから PROJECT_BASE_DIR に対する相対パスを取得します。"""
        try:
            abs_path_obj = Path(abs_path).resolve()
            relative_path = abs_path_obj.relative_to(config.PROJECT_BASE_DIR)
            return relative_path.as_posix()
        except ValueError as e:
            print("[エラー] 相対パス変換に失敗しました。")
            print(f" - 対象ファイル: {abs_path_obj}")
            print(f" - エラー内容: {e}")
            return None
        except Exception as e:
            print("[致命的エラー] 相対パス取得中に予期せぬエラーが発生しました。")
            print(f" - ファイル: {abs_path}")
            print(f" - 例外: {e}")
            return None
