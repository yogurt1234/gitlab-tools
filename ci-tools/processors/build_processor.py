import json
import sys
import config
import subprocess
import concurrent.futures
import io
import logging
from modules.gitlab.api_client import GitLabAPIClient


class BuildProcessor():

    def __init__(self, apiclient: GitLabAPIClient):
        self.apiclient = apiclient
        # ログの基本設定
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s [%(threadName)s] %(levelname)s: %(message)s',
            stream=sys.stdout
        )
        self.logger = logging.getLogger(__name__)

    def run(self):

        # if not build_targets:
        #    print("ビルド対象なし")
        #    return

        # feature
        # ラベル指定で必要なものと依存関係の考慮をする
        # ラベルはFull,BCM,Batch,Tenants等を想定する
        # ラベル指定で不足しているものがあるかは依存関係から特定する
        # 例えばラベルでBCMとしているが、Bしか変更していないケースでは、
        # CとDもビルドが必要である

        # プロジェクトの依存関係定義ファイルの読み込み
        with open(r"config/maven_dependency_build.json", "r", encoding="utf-8") as f:
            project_dependency = json.load(f)
        self.logger.info("Loaded project dependency configuration:")
        self.logger.info(project_dependency)

        # 対象とするプロジェクトを変更差分から取得する
        mr_diff = self.apiclient.get_merge_request_diff()
        # mr_diff = "{'id': 371201558, 'changes': [{'diff': '@@','new_path': 'ProjectC/diff_provider.py','old_path': 'ProjectC/diff_provider.py'},{'diff': '@@','new_path': 'ProjectC/diff_provider.py','old_path': 'ProjectC/diff_provider.py'}]}"
        # mr_diff = mr_diff.replace("'", "\"")
        # mr_diff = json.loads(mr_diff)

        # 依存関係とAPIの結果から対象を特定する
        build_target = self._detect_changed_projects(
            mr_diff, project_dependency)
        self.logger.info("Detected build targets: %s", build_target)

        # ビルドを実行する
        self._build(build_target, project_dependency)

    def _detect_changed_projects(self, mr_diff, project_dependency) -> list:
        # mr_diffからnew_pathとold_pathの全パスを収集
        paths = {
            change.get("new_path")
            for change in mr_diff.get("changes", [])
        } | {
            change.get("old_path")
            for change in mr_diff.get("changes", [])
        }

        # Noneでないパスについて、最上位ディレクトリ（プロジェクト名と仮定）を抽出
        initial_projects = list({p.split('/')[0] for p in paths if p})
        print("initial_projects")
        print(initial_projects)

        # 各プロジェクトのdependenciesをそのまま保持するマッピングを作成
        deps_mapping = {
            project["name"]: set(project.get("dependencies", []))
            for project in project_dependency["projects"]
        }

        # 初期の変更プロジェクトから、dependenciesを辿って影響範囲のプロジェクトを取得（DFS）
        visited = []
        stack = list(initial_projects)
        while stack:
            current = stack.pop()
            if current not in visited:
                visited.append(current)
                stack.extend(deps_mapping.get(current, []))

        # 各プロジェクトのorderに基づいて結果をソート
        order_mapping = {
            project["name"]: project["order"]
            for project in project_dependency["projects"]
        }
        return sorted(visited, key=lambda name: order_mapping.get(name, float('inf')))

    def _build(self, build_targets, project_dependency):
        # 設定ファイルから対象プロジェクトの定義を抽出
        projects_to_build = [
            project for project in project_dependency["projects"]
            if project["name"] in build_targets
        ]

        # 実行モードごとに分割（order順にソート）
        sequential_projects = sorted(
            [p for p in projects_to_build if p["execution_mode"] == "sequential"],
            key=lambda x: x["order"]
        )
        parallel_projects = sorted(
            [p for p in projects_to_build if p["execution_mode"] == "parallel"],
            key=lambda x: x["order"]
        )

        self.logger.info("=== Sequential Build ===")
        for project in sequential_projects:
            try:
                log_output = self._build_project(project)
                self.logger.info(log_output)
            except Exception as e:
                self.logger.error("Error in project %s: %s",
                                  project["name"], e)
                sys.exit(1)

        self.logger.info("=== Parallel Build ===")
        with concurrent.futures.ThreadPoolExecutor(max_workers=config.BUILD_CONCURRENCY) as executor:
            futures = {
                executor.submit(self._build_project, project): project
                for project in parallel_projects
            }
            for future in futures:
                try:
                    log_output = future.result()
                    self.logger.info(log_output)
                except Exception as e:
                    project = futures[future]
                    self.logger.error(
                        "Error in project %s: %s", project["name"], e)
                    sys.exit(1)

    def run_command(self, cmd, project_name, log_buffer):
        log_buffer.write(f"[{project_name}] Running command: {cmd}\n")
        result = subprocess.run(
            cmd, shell=True, capture_output=True, text=True)
        if result.stdout:
            log_buffer.write(f"[{project_name}] Output:\n{result.stdout}\n")
        if result.stderr:
            log_buffer.write(
                f"[{project_name}] Error Output:\n{result.stderr}\n")
        if result.returncode != 0:
            log_buffer.write(
                f"[{project_name}] Command failed with exit code {result.returncode}\n")
            raise RuntimeError(f"Build failed for {project_name}")
        log_buffer.write(f"[{project_name}] Command finished successfully.\n")

    def build_maven_project(self, project, log_buffer):
        cmd = f"cd ../{project['name']} && mvn clean install"
        log_buffer.write(cmd + "\n")
        log_buffer.write(f"Build finished for {project['name']}\n")
        self.run_command(cmd, project['name'], log_buffer)

    def _build_project(self, project):
        # 各プロジェクトのビルド処理を実行する
        log_buffer = io.StringIO()
        project_name = project["name"]
        project_type = project.get("type", "maven")
        log_buffer.write(
            f"\nStarting build for {project_name} (type: {project_type})\n")
        try:
            if project_type == "maven":
                self.build_maven_project(project, log_buffer)
            else:
                log_buffer.write(f"Unknown project type: {project_type}\n")
                raise ValueError(f"Unknown project type: {project_type}")
            log_buffer.write(f"Build finished for {project_name}\n")
        except Exception as e:
            log_buffer.write(f"Error building {project_name}: {e}\n")
            full_log = log_buffer.getvalue()
            log_buffer.close()
            self.logger.error(full_log)

        full_log = log_buffer.getvalue()
        log_buffer.close()
        return full_log


if __name__ == "__main__":
    hoge = BuildProcessor(None)
    hoge.run()
