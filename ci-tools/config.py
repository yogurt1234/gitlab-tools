import os

# CI環境かどうかを判定
if os.getenv("CI"):
    GITLAB_PROJECT_ID = os.getenv("CI_PROJECT_ID", "")
    GITLAB_MR_IID = os.getenv("CI_MERGE_REQUEST_IID", "")
    GITLAB_TOKEN = os.getenv("GITLAB_TOKEN", "")
    PROJECT_BASE_DIR = os.getenv("CI_PROJECT_DIR", "")
    PMD_PATH = os.getenv("PMD_PATH", "/bin/pmd")
    BUILD_CONCURRENCY = 10

else:
    PMD_PATH = os.getenv(
        "LOCAL_PMD_PATH", r"pmd.bat")
    GIT_DIFF_OPTION = os.getenv("GIT_DIFF_OPTION", "HEAD")
    PROJECT_BASE_DIR = ""
