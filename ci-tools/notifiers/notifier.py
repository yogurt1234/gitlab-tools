from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Tuple
from modules.gitlab.api_client import GitLabAPIClient


class ResultNotifyer(ABC):
    @abstractmethod
    def notify(self):  # pragma: no cover
        """
        結果通知をするためのメソッド。
        """
        pass


class GitLabCommentNotifier(ResultNotifyer):
    def __init__(self, gitlab_api_client: GitLabAPIClient):
        self.gitlab_api_client = gitlab_api_client

    def notify(self,
               violation_location: List[Tuple[Dict, Dict, str]],
               summary: Optional[str] = None) -> None:

        # 1つのコメントで集約する場合
        if summary:
            self.gitlab_api_client.post_note(summary)
            return

        # 対象行にレビューコメントを投稿する場合
        for diff_content, violation, relative_path in violation_location:
            position = {
                "base_sha": diff_content['base_sha'],
                "start_sha": diff_content['start_sha'],
                "head_sha": diff_content['head_sha'],
                "old_path": diff_content[relative_path]['old_path'],
                "new_path": diff_content[relative_path]['new_path'],
                "position_type": "text",
                "new_line": violation['beginline']
            }
            comment = "静的解析結果を確認してください " + " :cat: " + " <br>" + \
                violation['description'] + "<br>" + \
                violation['externalInfoUrl']

            self.gitlab_api_client.post_comment(comment, position)


class LocalResultNotifier(ResultNotifyer):
    """ローカル環境での結果通知を行うクラス"""

    def notify(self, violation_location):
        if not violation_location:
            print("解析結果: OK")
            return

        for diff_content, violation, relative_path in violation_location:
            print("解析結果:NG")
            print("ROW,RULE,DESCRIPTION,URL")
            print(str(violation['beginline']) + "," +
                  violation['rule'] + "," + violation['description'] + "," + violation['externalInfoUrl'])


class GitLabIssueCreator():
    pass
