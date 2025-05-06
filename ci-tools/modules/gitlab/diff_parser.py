from abc import ABC, abstractmethod
import re


class DiffParser(ABC):
    def __init__(self):
        # hunk ヘッダー（例: @@ -1,8 +1,14 @@）から新ファイル側の開始行番号と行数を抽出する正規表現
        self.hunk_re = re.compile(r'^@@ -\d+(?:,\d+)? \+(\d+)(?:,(\d+))? @@')

    @abstractmethod
    def parse(self):  # pragma: no cover
        pass

    def parse_hunk_header(self, diff_text: str) -> set:
        """
        hunkヘッダを解析します

        :param diff_text: 1 ファイル分の diff テキスト
        :return: 変更（追加）された行番号の set
        """
        changed_lines = set()
        current_line = None
        for line in diff_text.splitlines():
            if line.startswith('@@'):
                m = self.hunk_re.match(line)
                if m:
                    # 新ファイル側の開始行番号
                    current_line = int(m.group(1))
            else:
                if line.startswith('+') and not line.startswith('+++'):
                    # 追加行の場合、現在の行番号を記録
                    if current_line is not None:
                        changed_lines.add(current_line)
                        current_line += 1
                elif line.startswith('-') and not line.startswith('---'):
                    # 削除行は新ファイルに存在しないため current_line は進めない
                    continue
                else:
                    # コンテキスト行の場合は、行番号を進める
                    if current_line is not None:
                        current_line += 1
        return changed_lines


class GitLabDiffParser(DiffParser):
    """
    DiffParser クラスは、GitLab の MR API の diff 情報から
    変更されたファイル名と追加行番号を抽出するためのクラスです。
    """

    def parse(self, change_context: dict) -> dict:
        """
        GitLab の MR API 出力から、変更ファイルごとに以下の情報を含む辞書を生成します:
        - old_path: 変更前のファイルパス
        - new_path: 変更後のファイルパス
        - changed_lines: 変更行番号の set
        :param change_context: GitLab API の出力（JSON を辞書に変換したもの）
        :return: {base_sha: "",start_sha:"",head_sha:"",
                  new_path: {"old_path": old_path, "new_path": new_path, "changed_lines": {行番号, ...}}, ...}
        """
        result = {}
        print("MR INFO")
        print(change_context)
        # MRへのコメントに必要な情報を戻りに格納
        diff_refs = change_context.get("diff_refs", {})
        result['base_sha'] = diff_refs.get("base_sha")
        result['start_sha'] = diff_refs.get("start_sha")
        result['head_sha'] = diff_refs.get("head_sha")

        # ファイル単位での変更情報を抽出
        changes = change_context.get('changes', [])
        for change in changes:
            old_path = change.get('old_path')
            new_path = change.get('new_path')
            # # 拡張子が ".java" のものだけを対象
            # if not new_path.endswith(".java"):
            #     continue
            diff_text = change.get('diff')
            if new_path and diff_text:
                changed_lines = self.parse_hunk_header(diff_text)
                if changed_lines:
                    result[new_path] = {
                        "old_path": old_path,
                        "new_path": new_path,
                        "changed_lines": changed_lines,
                    }
        return result


class GitLocalDiffParser(DiffParser):
    """
    {"new_path": new_path, "changed_lines": {行番号, ...}}, ...}
    """

    def parse(self, diff_text) -> dict:
        results = {}   # {ファイル名: {変更行番号のset}}
        current_file = None
        new_line_num = None  # 現在の hunk の新ファイル側の行番号

        # diff 出力を 1 行ずつ処理
        for line in diff_text.splitlines():
            # ファイルヘッダの抽出: "diff --git a/xxx b/xxx"
            if line.startswith("diff --git"):
                match = re.match(r"diff --git a/.* b/(.+)", line)
                if match:
                    current_file = match.group(1)
                    # 現在のファイル用の変更行番号の set を初期化
                    if current_file not in results:
                        results[current_file] = set()
                # hunk が開始する前に new_line_num をクリア
                new_line_num = None

            # hunk ヘッダの抽出: @@ -old_start,old_count +new_start,new_count @@
            elif line.startswith("@@") and current_file:
                # 正規表現で新ファイル側の開始行番号と行数（省略時も考慮）を抽出
                # 例: @@ -23,7 +23,8 @@
                hunk_header_pattern = r"@@ -\d+(?:,\d+)? \+(\d+)(?:,(\d+))? @@"
                match = re.match(hunk_header_pattern, line)
                if match:
                    new_line_num = int(match.group(1))
                else:
                    new_line_num = None

            # hunk 本体の処理（行頭の記号で判定）
            elif current_file is not None and new_line_num is not None:
                if line.startswith(" "):
                    # コンテキスト行：そのまま新ファイル側の行番号をインクリメント
                    new_line_num += 1
                elif line.startswith("+"):
                    # 追加行の場合：現在の new_line_num を記録してインクリメント
                    results[current_file].add(new_line_num)
                    new_line_num += 1
                elif line.startswith("-"):
                    # 削除行の場合：新ファイル側には存在しないので、行番号はインクリメントしない
                    # ※削除行が対象外の場合は何もしない
                    continue
                else:
                    # その他（通常はない）は無視
                    continue

        return {
            filename: {"changed_lines": changed_lines}
            for filename, changed_lines in results.items()
        }
