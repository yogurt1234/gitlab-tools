from modules.gitlab.api_client import GitLabAPIClient
from processors.build_processor import BuildProcessor
import config
import os


def pipeline_generator_main():
    if os.getenv("CI"):
        # gitlab_apiの実行
        gitlab_api = GitLabAPIClient(
            project_id=config.GITLAB_PROJECT_ID,
            mr_iid=config.GITLAB_MR_IID,
            token=config.GITLAB_TOKEN
        )

        # ビルドの実行
        build_processor = BuildProcessor(gitlab_api)
        build_processor.run()
    else:
        # ローカルのビルド処理
        pass


if __name__ == "__main__":
    pipeline_generator_main()
