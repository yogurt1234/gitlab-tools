import requests
from typing import Dict, Any


class GitLabAPIClient:
    def __init__(self, project_id: str, mr_iid: str, token: str, base_url: str = "https://gitlab.com/api/v4"):
        """
        :param project_id: GitLab プロジェクトの ID(例: "66113052")
        :param mr_iid: マージリクエストの内部 ID(例: "11")
        :param token: GitLab のアクセストークン
        :param base_url: GitLab API のベース URL(デフォルトは "https://gitlab.com/api/v4")
        :param headers: APIのヘッダー情報
        """
        self.project_id = project_id
        self.mr_iid = mr_iid
        self.token = token
        self.base_url = base_url
        self.headers = {"PRIVATE-TOKEN": self.token}

    def get_merge_request_diff(self) -> list:
        """
        マージリクエストの diff 情報（変更内容）を取得します。
        """
        url = f"{self.base_url}/projects/{self.project_id}/merge_requests/{self.mr_iid}/changes"
        response = requests.get(url, headers=self.headers)
        response.raise_for_status()
        mr_info = response.json()
        return mr_info

    def post_comment(self, comment_text: str, position: Dict[str, Any]) -> dict:
        """
        マージリクエストの特定行にコメントを投稿します。
        """
        comment_url = f"{self.base_url}/projects/{self.project_id}/merge_requests/{self.mr_iid}/discussions"
        payload = {
            "body": comment_text,
            "position": position
        }
        response = requests.post(
            comment_url, headers=self.headers, json=payload)
        if response.status_code not in (200, 201):
            print(f"{comment_text}{position} のコメント投稿に失敗しました。")
            print(response.json())
        return response.json()

    def post_note(self, body: str) -> dict:
        """
        MR 全体（あるいはファイル単位）の一般ノートを投稿します。
        position を指定しないので、ファイル先頭にコメントしたいときに使います。
        """
        url = (
            f"{self.base_url}/projects/{self.project_id}"
            f"/merge_requests/{self.mr_iid}/notes"
        )
        payload = {"body": body}
        requests.post(url, headers=self.headers, json=payload)
