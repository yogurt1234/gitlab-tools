import config
import subprocess
from abc import ABC, abstractmethod
from modules.gitlab.diff_parser import GitLabDiffParser
from modules.gitlab.diff_parser import GitLocalDiffParser
from modules.gitlab.api_client import GitLabAPIClient


class DiffProvider(ABC):
    @abstractmethod
    def get_diff(self):  # pragma: no cover
        """
        diff 情報を取得するためのメソッド。
        各実装で具体的な diff 取得ロジックを実装してください。
        """
        pass


class GitLabDiffProvider(DiffProvider):
    def __init__(self, gitlab_api_client: GitLabAPIClient, diff_parser: GitLabDiffParser):
        self.gitlab_api_client = gitlab_api_client
        self.diff_parser = diff_parser

    def get_diff(self):
        # 1. GitLab API から MR の diff 情報を取得
        diff_data = self.gitlab_api_client.get_merge_request_diff()
        diff_parser = GitLabDiffParser()
        parsed_diff = diff_parser.parse(diff_data)
        return parsed_diff


class LocalDiffProvider(DiffProvider):
    def __init__(self, diff_parser: GitLocalDiffParser):
        self.diff_parser = diff_parser

    def get_diff(self):
        # ここでgit diffコマンドを実行する
        command = ["git", "diff"]
        if config.GIT_DIFF_OPTION:
            command.append(config.GIT_DIFF_OPTION)

        result = subprocess.run(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,    # 結果を文字列として受け取る
            encoding='utf-8',
            check=True    # エラー時に例外を発生させる
        )

        # parserで差分を解析する
        parsed_diff = self.diff_parser.parse(result.stdout)
        return parsed_diff
