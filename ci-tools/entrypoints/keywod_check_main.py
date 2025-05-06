import config
from modules.gitlab.api_client import GitLabAPIClient
from diff_providers.diff_provider import GitLabDiffProvider
from modules.gitlab.diff_parser import GitLabDiffParser
from notifiers.notifier import GitLabIssueCreator
from modules.keyword_check.keyword_check_executor import KeywordCheckExecutor
from processors.keywod_check_processor import KeywordCheckProcessor


def keyword_check_main():
    """キーワードチェックを実行するメイン処理"""
    # APIClientの作成
    gitlab_api = GitLabAPIClient(
        project_id=config.GITLAB_PROJECT_ID,
        mr_iid=config.GITLAB_MR_IID,
        token=config.GITLAB_TOKEN
    )

    # diffproviderの作成
    diff_provider = GitLabDiffProvider(gitlab_api, GitLabDiffParser())

    # keyword_check_executorの作成
    keywordcheck_executor = KeywordCheckExecutor()

    # GitLabIssueCreator
    issue_creator = GitLabIssueCreator(gitlab_api)

    # keyword_check_processorの作成と実行
    keyword_check_processor = KeywordCheckProcessor(
        diff_provider=diff_provider,
        keyword_check_executor=keywordcheck_executor,
        issue_creator=issue_creator
    )
    keyword_check_processor.run()


if __name__ == "__main__":
    keyword_check_main()
