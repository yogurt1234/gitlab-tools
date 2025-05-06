import argparse
import os
import sys
import config
import subprocess
from typing import Tuple
from pathlib import Path
from modules.gitlab.api_client import GitLabAPIClient
from modules.gitlab.diff_parser import GitLabDiffParser, GitLocalDiffParser
from modules.static_analysis.pmd_executor import PMDExecutor
from modules.static_analysis.eslint_executor import ESLintExecutor
from modules.static_analysis.prettier_executor import PrettierExecutor
from modules.static_analysis.abstract_static_analyzer import AbstractStaticAnalyzer
from processors.static_analysis_processor import StaticAnalysisProcessor
from diff_providers.diff_provider import GitLabDiffProvider, LocalDiffProvider
from notifiers.notifier import GitLabCommentNotifier, LocalResultNotifier


def static_analysis_main() -> None:
    """静的解析を実行するメイン処理"""

    # 静的解析アナライザを選択するための引数をパース
    args = _parse_arguments()

    try:
        # CI環境かローカルかを判定し、差分プロバイダと通知クラスを生成
        diff_provider, result_notifier = _prepare_environment()
        # 引数に応じてアナライザと対象のファイル拡張子を選択
        analyzer, target_extensions = _select_analyzer(
            args.analyzer)

        # 静的解析を実行するプロセッサを生成
        processor = StaticAnalysisProcessor(
            diff_provider=diff_provider,
            result_notifier=result_notifier,
            static_executor=analyzer,
            target_extensions=target_extensions
        )
        processor.run()

    except ValueError as ve:
        print(f"[設定エラー] {ve}")
        sys.exit(1)
    except (OSError, subprocess.SubprocessError) as se:
        print(f"[システムエラー] {se}")
        sys.exit(1)
    except Exception as e:
        print(f"[実行時エラー] {e}")
        sys.exit(1)


def _parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="静的解析の実行")
    parser.add_argument(
        "--analyzer",
        choices=["pmd", "eslint", "prettier"],
        required=True,
        help="使用する静的解析器を指定してください (pmd、eslint、prettierのいずれか)"
    )
    return parser.parse_args()


def _prepare_environment():
    """CI環境かローカルかを判定し、環境に応じて差分プロバイダクラスと通知クラスを生成する"""
    if os.getenv("CI"):
        gitlab_api = GitLabAPIClient(
            project_id=config.GITLAB_PROJECT_ID,
            mr_iid=config.GITLAB_MR_IID,
            token=config.GITLAB_TOKEN
        )
        diff_provider = GitLabDiffProvider(gitlab_api, GitLabDiffParser())
        result_notifier = GitLabCommentNotifier(gitlab_api)
    else:
        diff_provider = LocalDiffProvider(GitLocalDiffParser())
        result_notifier = LocalResultNotifier()

    return diff_provider, result_notifier


def _select_analyzer(
    analyzer_name: str,
    project_base: Path = Path(config.PROJECT_BASE_DIR)
) -> Tuple[AbstractStaticAnalyzer, Tuple[str, ...]]:
    """引数に応じてアナライザーと対象のファイル拡張子を返す"""
    if analyzer_name == "pmd":
        # PMDはルートから実行すればよいのでsrc_dirは不要
        analyzer = PMDExecutor(pmd_path=config.PMD_PATH)
        target_extensions = (".java",)
    elif analyzer_name == "eslint":
        analyzer = ESLintExecutor(
            eslint_cmd=["npx", "eslint"],
            src_dir=Path(project_base, "vue", "my-vue-app")
        )
        target_extensions = (".js", ".ts", ".vue")
    elif analyzer_name == "prettier":
        analyzer = PrettierExecutor(
            prettier_cmd=["npx", "prettier"],
            src_dir=Path(project_base, "vue", "my-vue-app")
        )
        target_extensions = (".js", ".ts", ".vue")
    else:
        raise ValueError(f"未対応の解析器が指定されました: {analyzer_name}")

    return analyzer, target_extensions


if __name__ == "__main__":
    static_analysis_main()
